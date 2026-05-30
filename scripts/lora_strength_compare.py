import copy
import itertools
import json
import os
import datetime
import math
import gradio as gr
from PIL import Image, ImageDraw, ImageFont

import modules.scripts as scripts
from modules import processing, shared
from modules.processing import Processed, process_images
from modules.paths import models_path

OVERLAY_FONT_SIZE = 28
OVERLAY_PADDING = 8
LORA_DIR = os.path.join(models_path, "Lora")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
MAX_SLOTS = 8
NONE_LABEL = "(なし)"


# ── 設定保存・読み込み ────────────────────────────────

def _load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_config(data: dict):
    try:
        cfg = _load_config()
        cfg.update(data)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── LoRAスキャン ──────────────────────────────────────

def _scan_loras():
    result = []
    if not os.path.isdir(LORA_DIR):
        return result
    for root, _, files in os.walk(LORA_DIR):
        for f in sorted(files):
            if f.lower().endswith((".safetensors", ".ckpt", ".pt")):
                rel = os.path.relpath(os.path.join(root, f), LORA_DIR)
                result.append(os.path.splitext(rel)[0].replace("\\", "/"))
    return result

def _short(name):
    return name.split("/")[-1]


# ── トリガーワード読み込み ─────────────────────────────

def _get_trigger_words(lora_rel: str) -> str:
    """
    LoRA の相対パス（拡張子なし）からトリガーワードを返す。
    優先順: .json (activation text) → .metadata.json (civitai.trainedWords) → .civitai.info (trainedWords)
    """
    base = os.path.join(LORA_DIR, lora_rel)

    # .json sidecar
    try:
        with open(base + ".json", encoding="utf-8") as f:
            d = json.load(f)
        text = d.get("activation text", "").strip().strip(",").strip()
        if text:
            return text
    except Exception:
        pass

    # .metadata.json sidecar
    try:
        with open(base + ".metadata.json", encoding="utf-8") as f:
            d = json.load(f)
        words = [w.strip() for w in d.get("civitai", {}).get("trainedWords", []) if w.strip()]
        if words:
            return ", ".join(words)
    except Exception:
        pass

    # .civitai.info sidecar
    try:
        with open(base + ".civitai.info", encoding="utf-8") as f:
            d = json.load(f)
        words = [w.strip() for w in d.get("trainedWords", []) if w.strip()]
        if words:
            return ", ".join(words)
    except Exception:
        pass

    return ""


def _collect_triggers(slot_values: list[str]) -> str:
    """選択中のLoRA全員のトリガーワードをまとめて返す（重複除去）。"""
    seen, parts = set(), []
    for name in slot_values:
        if not name or name == NONE_LABEL:
            continue
        tw = _get_trigger_words(name)
        for token in (t.strip() for t in tw.split(",") if t.strip()):
            if token.lower() not in seen:
                seen.add(token.lower())
                parts.append(token)
    return ", ".join(parts)


# ── 計算 ─────────────────────────────────────────────

def _strength_range(lo, hi, step):
    vals, v = [], lo
    while v <= hi + step * 0.01:
        vals.append(round(v, 3))
        v += step
    return vals

def _calc_count(*args):
    # args: slot_0..slot_7, s_min, s_max, s_step, combo_n
    slots   = args[:MAX_SLOTS]
    s_min, s_max, s_step, combo_n = args[MAX_SLOTS:]
    n = int(combo_n)
    selected = [s for s in slots if s and s != NONE_LABEL]
    total_loras = len(selected)
    if total_loras == 0 or n < 1 or n > total_loras:
        return '<div class="lsc-count">—</div>'
    combos    = math.comb(total_loras, n)
    strengths = len(_strength_range(s_min, s_max, s_step))
    total     = combos * (strengths ** n)
    return (
        f'<div class="lsc-count">'
        f'選択 {total_loras} 本 → '
        f'C({total_loras},{n}) = {combos} 組 × '
        f'{strengths}^{n} = {strengths**n} 強度パターン = '
        f'合計 {total} 枚'
        f'</div>'
    )


# ── オーバーレイ描画 ──────────────────────────────────

def _load_font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf", "NotoSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()

def _draw_overlay(img, lines):
    img = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(OVERLAY_FONT_SIZE)
    p = OVERLAY_PADDING

    bboxes = [draw.textbbox((0, 0), l, font=font) for l in lines]
    tw = max(b[2] - b[0] for b in bboxes)
    lh = max(b[3] - b[1] for b in bboxes)
    th = lh * len(lines) + p * (len(lines) - 1)

    x, y = p, img.height - th - p * 2
    draw.rectangle([x, y, x + tw + p * 2, y + th + p * 2], fill=(0, 0, 0, 170))
    for i, line in enumerate(lines):
        draw.text((x + p, y + p + i * (lh + p)), line, fill=(255, 255, 255, 240), font=font)

    return Image.alpha_composite(img, overlay).convert("RGB")


# ── CSS ──────────────────────────────────────────────

CSS = """
.lsc-group {
    border: 1px solid var(--border-color-primary);
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 6px;
}
.lsc-label {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--body-text-color-subdued);
    text-transform: uppercase;
    margin-bottom: 4px;
}
.lsc-count { font-size: 13px; color: var(--body-text-color); padding: 6px 0; }
.lsc-slot  { margin-top: 4px; }
"""


# ── Script ───────────────────────────────────────────

class Script(scripts.Script):
    def title(self):
        return "LoRA Strength Compare"

    def show(self, is_img2img):
        return True

    def ui(self, is_img2img):
        gr.HTML(f"<style>{CSS}</style>")

        loras   = [NONE_LABEL] + _scan_loras()
        cfg     = _load_config()
        saved   = cfg.get("slots", [NONE_LABEL] * MAX_SLOTS)
        # 保存スロット数が足りない場合は補完
        saved   = (saved + [NONE_LABEL] * MAX_SLOTS)[:MAX_SLOTS]

        # ── LoRA選択スロット ──
        with gr.Group(elem_classes="lsc-group"):
            gr.HTML('<div class="lsc-label">LoRA リスト</div>')

            slots = []
            rows  = []
            for i in range(MAX_SLOTS):
                val = saved[i] if saved[i] in loras else NONE_LABEL
                with gr.Row(visible=(i < 2), elem_classes="lsc-slot") as row:
                    d = gr.Dropdown(
                        choices=loras,
                        value=val,
                        label=f"LoRA {i + 1}",
                        show_label=False,
                    )
                slots.append(d)
                rows.append(row)

            visible_count = gr.State(value=2)

            with gr.Row():
                add_btn = gr.Button("＋ 追加", size="sm")
                rem_btn = gr.Button("－ 削除", size="sm")

            trigger_preview = gr.Textbox(
                label="検出されたトリガーワード",
                value=_collect_triggers(saved),
                interactive=False,
                lines=2,
            )

        def _add(n):
            new_n = min(n + 1, MAX_SLOTS)
            return [new_n] + [gr.update(visible=(i < new_n)) for i in range(MAX_SLOTS)]

        def _remove(n):
            new_n = max(n - 1, 1)
            return [new_n] + [gr.update(visible=(i < new_n)) for i in range(MAX_SLOTS)]

        add_btn.click(fn=_add, inputs=[visible_count], outputs=[visible_count] + rows)
        rem_btn.click(fn=_remove, inputs=[visible_count], outputs=[visible_count] + rows)

        # ── 強度・組み合わせ ──
        with gr.Group(elem_classes="lsc-group"):
            gr.HTML('<div class="lsc-label">強度スイープ</div>')
            with gr.Row():
                s_min  = gr.Slider(0.0, 2.0, value=0.5, step=0.1, label="Min")
                s_max  = gr.Slider(0.0, 2.0, value=1.0, step=0.1, label="Max")
                s_step = gr.Slider(0.1, 1.0, value=0.1, step=0.1, label="Step")

        with gr.Group(elem_classes="lsc-group"):
            gr.HTML('<div class="lsc-label">組み合わせ</div>')
            combo_n = gr.Slider(1, MAX_SLOTS, value=1, step=1, label="同時使用本数")

        count_label = gr.HTML(value=_calc_count(*([NONE_LABEL] * MAX_SLOTS), 0.5, 1.0, 0.1, 1))

        count_inputs = slots + [s_min, s_max, s_step, combo_n]
        for ctrl in count_inputs:
            ctrl.change(fn=_calc_count, inputs=count_inputs, outputs=count_label)

        # スロット変更時: 保存 + トリガープレビュー更新
        def _on_slot_change(*vals):
            _save_config({"slots": list(vals)})
            return _collect_triggers(list(vals))

        for d in slots:
            d.change(fn=_on_slot_change, inputs=slots, outputs=[trigger_preview])

        return slots + [s_min, s_max, s_step, combo_n]

    def run(self, p, *args):
        slots_vals          = list(args[:MAX_SLOTS])
        s_min, s_max, s_step, combo_n = args[MAX_SLOTS:]

        selected = [s for s in slots_vals if s and s != NONE_LABEL]
        if not selected:
            return Processed(p, [], p.seed, "LoRA を1本以上選択してください")

        n = int(combo_n)
        if n > len(selected):
            return Processed(p, [], p.seed, f"選択LoRA数({len(selected)})より組み合わせ本数({n})が多いです")

        combos    = list(itertools.combinations(selected, n))
        strengths = _strength_range(s_min, s_max, s_step)

        processing.fix_seed(p)
        base_prompt = p.prompt
        trigger_words = _collect_triggers(selected)

        save_dir = os.path.join(p.outpath_samples, "lora-compare")
        os.makedirs(save_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

        cell_imgs, all_seeds, all_prompts, infotexts = [], [], [], []

        for combo in combos:
            for strength_pattern in itertools.product(strengths, repeat=n):
                pc = copy.copy(p)
                pc.do_not_save_samples = True
                pc.do_not_save_grid = True

                tags = " ".join(
                    f"<lora:{_short(name)}:{s}>"
                    for name, s in zip(combo, strength_pattern)
                )
                combo_triggers = _collect_triggers(list(combo))
                pc.prompt = ", ".join(x for x in [base_prompt, combo_triggers, tags] if x)

                result = process_images(pc)
                if not result.images:
                    continue

                lines = [f"{_short(name)}  {s}" for name, s in zip(combo, strength_pattern)]
                img = _draw_overlay(result.images[0], lines)

                fname = ts + "_" + "_".join(
                    f"{_short(name)}-{s}" for name, s in zip(combo, strength_pattern)
                )
                img.save(os.path.join(save_dir, f"{fname}.png"))

                cell_imgs.append(img)
                all_seeds.append(result.seed)
                all_prompts.append(pc.prompt)
                infotexts.append(result.infotexts[0] if result.infotexts else "")

        return Processed(
            p, cell_imgs,
            all_seeds[0] if all_seeds else p.seed, "",
            all_prompts=all_prompts,
            infotexts=infotexts,
        )

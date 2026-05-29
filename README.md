# sd-webui-lora-strength-compare

[Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) / Forge 向けスクリプト拡張。  
選択した LoRA の強度を全パターン組み合わせて一括生成し、比較を容易にします。

## 機能

- LoRA を最大 8 本まで個別に選択
- 強度スイープの範囲を Min / Max / Step で指定
- 同時使用本数を指定してすべての組み合わせを生成
- LoRA ごとに独立した強度の全パターンを生成（例：2本×3強度 = 9パターン）
- 各画像の左下に LoRA 名と強度をオーバーレイ表示
- 生成画像を `outputs/lora-compare/` に自動保存
- 選択した LoRA をセッション間で記憶

## 使い方

1. **txt2img** または **img2img** を開く
2. 下部の **Scripts** から **LoRA Strength Compare** を選択
3. ドロップダウンで LoRA を選択（＋/－ボタンでスロットを追加・削除）
4. 強度の範囲と同時使用本数を設定
5. 合計枚数を確認してから **Generate**

プロンプト・Seed・Steps・CFG・サンプラーは txt2img / img2img の設定をそのまま使用します。

## 例

- LoRA 4本選択、同時使用本数 = 2、強度 = [0.5, 0.8, 1.0]
- C(4, 2) = 6 組 × 3² = 9 強度パターン = **合計 54 枚**

## 注意

- Seed は全生成で固定されるため公平な比較が可能
- 画像は WebUI の保存設定に関わらず `outputs/lora-compare/` に個別保存

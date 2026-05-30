# sd-webui-lora-strength-compare

選択した LoRA の強度を全パターン組み合わせて一括生成し、比較できる Forge Neo 拡張機能です

## 機能

- LoRA を最大 8 本まで個別に選択
- 強度スイープの範囲を Min / Max / Step で指定
- 同時使用本数を指定してすべての組み合わせを生成
- LoRA ごとに独立した強度の全パターンを生成（例：2本 × 3強度 = 9パターン）
- `.json` / `.metadata.json` / `.civitai.info` からトリガーワードを自動検出してプロンプトに付加
- 各画像の左下に LoRA 名と強度をオーバーレイ表示
- 生成画像を txt2img / img2img の出力先下の `lora-compare/` フォルダに自動保存
- 選択した LoRA をセッション間で記憶

## インストール方法

1. WebUI を起動
2. **Extensions** タブ → **Install from URL** を開く
3. 以下の URL を貼り付けて Install をクリック：
   ```
   https://github.com/ranran141/sd-webui-lora-strength-compare
   ```
4. WebUI を再起動

## 動作環境

- Forge Neo

## 使い方

txt2img または img2img の **Scripts** ドロップダウンから **LoRA Strength Compare** を選択します。

1. ドロップダウンで **LoRA を選択**（＋/－ボタンでスロットを追加・削除）
   - トリガーワードがある場合、「検出されたトリガーワード」欄に自動表示される
2. **強度スイープ**の Min / Max / Step を設定
3. **同時使用本数**を設定
   - 例：LoRA 3本、本数 2 → C(3,2) = 3組
4. 合計枚数を確認してから txt2img の **Generate** をクリック

プロンプト・Seed・Steps・CFG・サンプラーは txt2img / img2img の設定をそのまま使用します。

### 枚数の計算式

```
C(選択本数, 同時使用本数) × 強度パターン数^同時使用本数 = 合計枚数
```

例：LoRA 4本、同時使用 2、強度 [0.5, 0.8, 1.0]
→ C(4,2) = 6組 × 3² = 9パターン = **54枚**

### 保存先

txt2img / img2img の出力先設定に従い、その下に `lora-compare/` フォルダを作成して保存します。  
例：出力先が `Image` の場合 → `Image/lora-compare/`

### トリガーワードの自動検出

LoRA と同名のサイドカーファイルがある場合、トリガーワードを自動でプロンプトに付加します。

| ファイル | 読み込むフィールド |
|---------|----------------|
| `.json` | `activation text` |
| `.metadata.json` | `civitai.trainedWords` |
| `.civitai.info` | `trainedWords` |

## 更新履歴

### v1.0.0

- 初回リリース

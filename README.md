# sd-webui-lora-strength-compare

A script extension for [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) / Forge that generates all strength combinations for selected LoRAs.

## Features

- Select up to 8 LoRAs individually via dropdown
- Set strength sweep range (Min / Max / Step)
- Set how many LoRAs to combine at once
- Generates every strength pattern independently per LoRA (`itertools.product`)
- Overlays LoRA name + strength on each output image
- Saves results to `outputs/lora-compare/`
- Remembers selected LoRAs across sessions

## Usage

1. Open **txt2img** or **img2img**
2. Scroll down to **Scripts** and select **LoRA Strength Compare**
3. Pick LoRAs from the dropdowns (use ＋/－ to add or remove slots)
4. Set strength range and combination size
5. Check the estimated image count, then click **Generate**

The script uses the prompt, seed, steps, CFG, and sampler already set in txt2img/img2img.

## Example

- 4 LoRAs selected, combination size = 2, strengths = [0.5, 0.8, 1.0]
- C(4, 2) = 6 combos × 3² = 9 strength patterns = **54 images**

## Notes

- Seed is fixed across all generations for fair comparison
- Images are saved individually to `outputs/lora-compare/` regardless of WebUI save settings

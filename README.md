# mic-tune

Auto-adjusts OBS audio filter settings for your mic. Records room noise and your voice, analyzes the spectrum, and outputs optimized OBS filter settings.

## Install

```bash
pip install sounddevice numpy scipy
```

## Usage

```bash
python3 mic_tune.py
```

1. Make sure your mic is plugged in and selected as the default input device
2. Stay quiet for 5 seconds (records room noise)
3. Talk naturally for 10 seconds
4. Get optimized OBS filter settings

## What it calculates

- **Noise Gate** — thresholds based on your actual noise floor
- **Compressor** — ratio and threshold based on your dynamic range
- **Equalizer** — frequency cuts where your room resonates, boosts for voice clarity

## OBS Setup

Add these filters in order (top to bottom):
1. Noise Suppression (RNNoise)
2. Noise Gate
3. Compressor
4. Equalizer (VST 2.x plugin)

## Windows

Works on Windows too. Just make sure your mic is set as the default recording device in Windows Sound Settings.

```bash
pip install sounddevice numpy scipy
python mic_tune.py
```

# mic-tune

Measures your room noise and voice, then outputs tuned OBS filter settings for your mic.

## Install

```bash
pip install sounddevice numpy scipy
```

## Usage

```bash
python3 mic_tune.py
```

1. Set your mic as the default input device
2. Stay quiet for 5 seconds (records room noise)
3. Talk naturally for 10 seconds
4. Get optimized OBS filter settings

## What it calculates

- **Noise Gate.** Thresholds based on your actual noise floor
- **Compressor.** Ratio and threshold based on your dynamic range
- **Equalizer.** Cuts where your room resonates, boosts for voice clarity

## OBS Setup

Add these filters in order (top to bottom):
1. Noise Suppression (RNNoise)
2. Noise Gate
3. Compressor
4. Equalizer (VST 2.x plugin)

## Windows

Works on Windows too. Set your mic as the default recording device in Windows Sound Settings.

```bash
pip install sounddevice numpy scipy
python mic_tune.py
```

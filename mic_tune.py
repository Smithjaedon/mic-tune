#!/usr/bin/env python3
"""
mic-tune: Auto-adjust OBS audio filters for your Blue Yeti.
Records room noise + your voice, analyzes the spectrum,
and outputs optimized OBS filter settings.

Usage: python3 mic_tune.py
"""

import numpy as np
import sounddevice as sd
import sys
import json

SAMPLE_RATE = 44100
CHANNELS = 1
DTYPE = 'float32'


def record_audio(duration, prompt):
    """Record audio from the default input device."""
    print(f"\n{'='*50}")
    print(f"  {prompt}")
    print(f"  Recording for {duration} seconds...")
    print(f"{'='*50}")
    
    frames = int(SAMPLE_RATE * duration)
    recording = sd.rec(frames, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE)
    sd.wait()
    return recording.flatten()


def analyze_spectrum(audio, label=""):
    """Compute frequency spectrum of audio."""
    n = len(audio)
    fft = np.fft.rfft(audio * np.hanning(n))
    magnitude = np.abs(fft) / n
    freqs = np.fft.rfftfreq(n, 1.0 / SAMPLE_RATE)
    
    # Convert to dB
    magnitude_db = 20 * np.log10(np.maximum(magnitude, 1e-10))
    
    # Overall RMS level
    rms = np.sqrt(np.mean(audio ** 2))
    rms_db = 20 * np.log10(max(rms, 1e-10))
    
    return {
        'freqs': freqs,
        'magnitude_db': magnitude_db,
        'rms_db': rms_db,
        'label': label
    }


def get_band_energy(freqs, mag_db, low, high):
    """Get average energy in a frequency band."""
    mask = (freqs >= low) & (freqs <= high)
    if np.any(mask):
        return np.mean(mag_db[mask])
    return -100.0


def calculate_noise_gate(noise_floor_db):
    """Calculate noise gate thresholds based on noise floor."""
    # Gate should open when voice is clearly above noise
    # Close threshold: slightly above noise floor
    close_threshold = round(noise_floor_db + 3, 1)
    # Open threshold: voice should be well above noise
    open_threshold = round(noise_floor_db + 10, 1)
    
    return {
        'close_threshold': close_threshold,
        'open_threshold': open_threshold,
        'attack': 10,
        'hold': 200,
        'release': 100
    }


def calculate_compressor(voice_db, noise_db):
    """Calculate compressor settings based on dynamic range."""
    # Determine dynamic range
    headroom = voice_db - noise_db
    
    # Ratio based on how dynamic the recording is
    if headroom > 40:
        ratio = 4
        threshold = round(voice_db - 15, 1)
    elif headroom > 30:
        ratio = 3
        threshold = round(voice_db - 12, 1)
    else:
        ratio = 2
        threshold = round(voice_db - 10, 1)
    
    return {
        'ratio': f'{ratio}:1',
        'threshold': threshold,
        'attack': 6,
        'release': 100
    }


def calculate_eq(noise_spec, voice_spec):
    """Calculate EQ settings based on frequency analysis."""
    freqs_n = noise_spec['freqs']
    freqs_v = voice_spec['freqs']
    mag_n = noise_spec['magnitude_db']
    mag_v = voice_spec['magnitude_db']
    
    # Find where room resonance lives (peaks in noise that aren't in voice)
    # Low rumble (below 80 Hz)
    low_energy = get_band_energy(freqs_n, mag_n, 20, 80)
    
    # Boxy room frequencies (200-500 Hz)
    boxy_energy = get_band_energy(freqs_n, mag_n, 200, 500)
    boxy_voice = get_band_energy(freqs_v, mag_v, 200, 500)
    
    # Presence/clarity (2-5 kHz)
    presence_energy = get_band_energy(freqs_v, mag_v, 2000, 5000)
    
    # High hiss (above 10 kHz)
    hiss_energy = get_band_energy(freqs_n, mag_n, 10000, 20000)
    
    # Build EQ recommendations
    eq = []
    
    # High-pass filter
    if low_energy > -50:
        eq.append({
            'type': 'High Pass Filter',
            'frequency': 80,
            'gain': 'cut',
            'note': 'Removes low rumble and room resonance'
        })
    
    # Boxy room cut
    boxy_ratio = boxy_energy - boxy_voice
    if boxy_ratio > -3:  # Room has more energy here than voice
        eq.append({
            'type': 'Peaking',
            'frequency': 300,
            'gain_db': -6,
            'q': 1.0,
            'note': f'Cuts boxy room sound (room has {abs(boxy_ratio):.1f}dB more energy here)'
        })
    
    # Presence boost
    eq.append({
        'type': 'Peaking',
        'frequency': 3000,
        'gain_db': 3,
        'q': 1.5,
        'note': 'Boosts vocal clarity and presence'
    })
    
    # High shelf for hiss
    if hiss_energy > -40:
        eq.append({
            'type': 'High Shelf',
            'frequency': 10000,
            'gain_db': -3,
            'note': 'Reduces high-frequency hiss'
        })
    
    return eq


def print_obs_settings(noise_gate, compressor, eq, noise_db, voice_db):
    """Print OBS filter settings in a copy-pasteable format."""
    print(f"\n{'='*60}")
    print(f"  YOUR OPTIMIZED OBS FILTER SETTINGS")
    print(f"{'='*60}")
    
    print(f"\n  Noise Floor: {noise_db:.1f} dB")
    print(f"  Voice Level: {voice_db:.1f} dB")
    print(f"  Dynamic Range: {voice_db - noise_db:.1f} dB")
    
    print(f"\n{'─'*60}")
    print(f"  1. NOISE SUPPRESSION")
    print(f"{'─'*60}")
    print(f"  Method: RNNoise")
    print(f"  (This kills static noise — fans, hiss, electrical hum)")
    
    print(f"\n{'─'*60}")
    print(f"  2. NOISE GATE")
    print(f"{'─'*60}")
    print(f"  Close threshold:  {noise_gate['close_threshold']} dB")
    print(f"  Open threshold:   {noise_gate['open_threshold']} dB")
    print(f"  Attack:           {noise_gate['attack']} ms")
    print(f"  Hold:             {noise_gate['hold']} ms")
    print(f"  Release:          {noise_gate['release']} ms")
    print(f"  (Cuts audio when you're not talking)")
    
    print(f"\n{'─'*60}")
    print(f"  3. COMPRESSOR")
    print(f"{'─'*60}")
    print(f"  Ratio:            {compressor['ratio']}")
    print(f"  Threshold:        {compressor['threshold']} dB")
    print(f"  Attack:           {compressor['attack']} ms")
    print(f"  Release:          {compressor['release']} ms")
    print(f"  (Evens out your volume)")
    
    print(f"\n{'─'*60}")
    print(f"  4. EQUALIZER (VST 2.x plugin)")
    print(f"{'─'*60}")
    for i, band in enumerate(eq, 1):
        print(f"  Band {i}: {band['type']}", end="")
        if 'frequency' in band:
            print(f" @ {band['frequency']} Hz", end="")
        if 'gain_db' in band:
            print(f" | {band['gain_db']:+.0f} dB", end="")
        elif 'gain' in band:
            print(f" | {band['gain']}", end="")
        if 'q' in band:
            print(f" | Q: {band['q']}", end="")
        print()
        print(f"           {band['note']}")
    
    print(f"\n{'─'*60}")
    print(f"  ADD THESE IN ORDER (top to bottom in OBS):")
    print(f"  1 → Noise Suppression")
    print(f"  2 → Noise Gate")
    print(f"  3 → Compressor")
    print(f"  4 → Equalizer (VST 2.x)")
    print(f"{'─'*60}")
    
    # Also output as JSON for easy copy
    settings = {
        'noise_gate': noise_gate,
        'compressor': compressor,
        'eq': eq,
        'stats': {
            'noise_floor_db': round(noise_db, 1),
            'voice_level_db': round(voice_db, 1),
            'dynamic_range_db': round(voice_db - noise_db, 1)
        }
    }
    
    json_path = '/Users/jaedonsmith/coding/mic-tune/obs_settings.json'
    with open(json_path, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"\n  Settings also saved to: {json_path}")


def main():
    print(f"\n{'='*60}")
    print(f"  mic-tune — Auto-adjust your OBS audio filters")
    print(f"{'='*60}")
    print(f"\n  This will record your room noise and voice,")
    print(f"  then calculate optimal OBS filter settings.")
    print(f"\n  Make sure your Blue Yeti is connected and selected")
    print(f"  as the default input device.")
    
    # Step 1: Record silence (room noise)
    noise_audio = record_audio(5, "STEP 1: Stay quiet for 5 seconds...")
    
    # Step 2: Record voice
    voice_audio = record_audio(10, "STEP 2: Talk naturally for 10 seconds!")
    
    # Step 3: Analyze
    print(f"\n{'='*50}")
    print(f"  Analyzing audio...")
    print(f"{'='*50}")
    
    noise_spec = analyze_spectrum(noise_audio, "Room Noise")
    voice_spec = analyze_spectrum(voice_audio, "Voice")
    
    noise_db = noise_spec['rms_db']
    voice_db = voice_spec['rms_db']
    
    print(f"\n  Room noise level: {noise_db:.1f} dB")
    print(f"  Voice level:      {voice_db:.1f} dB")
    print(f"  Difference:       {voice_db - noise_db:.1f} dB")
    
    if voice_db - noise_db < 15:
        print(f"\n  ⚠️  WARNING: Low difference between voice and noise.")
        print(f"      Try getting closer to the mic or using cardioid mode.")
    
    # Step 4: Calculate settings
    noise_gate = calculate_noise_gate(noise_db)
    compressor = calculate_compressor(voice_db, noise_db)
    eq = calculate_eq(noise_spec, voice_spec)
    
    # Step 5: Print results
    print_obs_settings(noise_gate, compressor, eq, noise_db, voice_db)


if __name__ == '__main__':
    main()

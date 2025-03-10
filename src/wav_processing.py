"""
WAV Processing - Core audio processing functions
"""

import struct
import numpy as np
from sample_utils import get_sample_format_info


def _apply_gain(sample_value, gain, min_value, max_value):
    """Apply gain to a sample and clip to bounds."""
    
    sample_value = int(sample_value * gain)
    return max(min_value, min(max_value, sample_value))


def _apply_anti_distortion(sample_value, threshold, max_value):
    """Apply anti-distortion to a sample using soft clipping."""
    
    abs_sample = abs(sample_value)
    thresh_val = max_value * threshold
    
    if abs_sample > thresh_val:
        sign = 1 if sample_value > 0 else -1
        excess = abs_sample - thresh_val
        clipped = thresh_val + (excess - (excess**3) / (3 * thresh_val**2))
        sample_value = int(sign * min(max_value, max(thresh_val, clipped)))
        return max(-max_value - 1, min(max_value, sample_value))
    
    return sample_value


def process_standard_samples(wav_data, bits_per_sample, gain=None, threshold=None):
    """
    Process 8, 16, or 32-bit samples with gain or anti-distortion.
    
    Args:
        wav_data (bytes): Raw audio data
        bits_per_sample (int): Bits per sample
        gain (float, optional): Gain factor for amplification
        threshold (float, optional): Threshold for anti-distortion
        
    Returns:
        bytes: Processed audio data
        
    Raises:
        ValueError: If both gain and threshold are provided or neither
    """
    
    if (gain is None and threshold is None) or (gain is not None and threshold is not None):
        raise ValueError("Exactly one of gain or threshold must be provided")
    
    sample_format, max_value, zero_value = get_sample_format_info(bits_per_sample)
    sample_size = bits_per_sample // 8
    sample_count = len(wav_data) // sample_size
    
    format_str = '<' + sample_format * sample_count
    samples = list(struct.unpack(format_str, wav_data))
    
    min_value = -max_value - 1 if zero_value == 0 else -zero_value
    is_8bit = bits_per_sample == 8
    
    for i in range(sample_count):
        sample_value = samples[i] - zero_value if is_8bit else samples[i]
        
        if gain is not None:
            sample_value = _apply_gain(sample_value, gain, min_value, max_value)
        else:  # threshold is not None
            sample_value = _apply_anti_distortion(sample_value, threshold, max_value)
        
        samples[i] = sample_value + zero_value if is_8bit else sample_value
    
    return struct.pack(format_str, *samples)


def process_24bit_samples(wav_data, gain=None, threshold=None):
    """
    Process 24-bit samples with gain or anti-distortion.
    
    Args:
        wav_data (bytes): Raw audio data
        gain (float, optional): Gain factor for amplification
        threshold (float, optional): Threshold for anti-distortion
        
    Returns:
        bytes: Processed audio data
    """
    
    _, max_value, _ = get_sample_format_info(24)
    sample_size = 3
    sample_count = len(wav_data) // sample_size
    new_data = bytearray(len(wav_data))
    
    for i in range(sample_count):
        byte_pos = i * sample_size
        b1 = wav_data[byte_pos]
        b2 = wav_data[byte_pos + 1]
        b3 = wav_data[byte_pos + 2]
        
        sample_value = b1 | (b2 << 8) | (b3 << 16)
        
        if sample_value & 0x800000:
            sample_value = sample_value - 0x1000000
        
        if gain is not None:
            sample_value = int(sample_value * gain)
            sample_value = max(-max_value, min(max_value, sample_value))
        elif threshold is not None:
            abs_sample = abs(sample_value)
            thresh_val = max_value * threshold
            if abs_sample > thresh_val:
                sign = 1 if sample_value > 0 else -1
                excess = abs_sample - thresh_val
                clipped = thresh_val + (excess - (excess**3) / (3 * thresh_val**2))
                sample_value = int(sign * min(max_value, clipped))
        
        if sample_value < 0:
            sample_value = sample_value + 0x1000000
        new_data[byte_pos] = sample_value & 0xFF
        new_data[byte_pos + 1] = (sample_value >> 8) & 0xFF
        new_data[byte_pos + 2] = (sample_value >> 16) & 0xFF
    
    return bytes(new_data)


def process_noise_removal(wav_data, bits_per_sample, strength, sample_rate, profile_data=None):
    """
    Process audio samples with noise removal using spectral subtraction
    
    Args:
        wav_data (bytes): Raw audio data
        bits_per_sample (int): Bits per sample
        strength (str): Noise reduction strength ('low', 'medium', 'high')
        sample_rate (int): Sample rate in Hz
        profile_data (bytes, optional): Noise profile data
        
    Returns:
        bytes: Processed audio data
    """
    # Strength factors (0.0 to 1.0)
    strength_map = {'low': 0.3, 'medium': 0.6, 'high': 0.9}
    reduction_factor = strength_map[strength]
    
    # Get sample format info
    sample_format, max_value, zero_value = get_sample_format_info(bits_per_sample)
    sample_size = bits_per_sample // 8
    sample_count = len(wav_data) // sample_size
    
    # Handle 24-bit separately
    if bits_per_sample == 24:
        samples = []
        for i in range(sample_count):
            byte_pos = i * 3
            sample_value = (wav_data[byte_pos] | 
                          (wav_data[byte_pos + 1] << 8) | 
                          (wav_data[byte_pos + 2] << 16))
            if sample_value & 0x800000:
                sample_value -= 0x1000000
            samples.append(sample_value)
    else:
        format_str = '<' + sample_format * sample_count
        samples = list(struct.unpack(format_str, wav_data))
        if bits_per_sample == 8:
            samples = [s - zero_value for s in samples]
    
    # FFT window size (power of 2)
    window_size = 1024
    hop_size = window_size // 2
    processed_samples = np.zeros(len(samples))
    window_count = np.zeros(len(samples))
    
    # Hanning window
    window = np.hanning(window_size)
    
    # Simple noise profile (white noise assumption if no profile provided)
    noise_profile = np.ones(window_size) * (max_value * 0.01 * reduction_factor)
    if profile_data:
        profile_sample_count = len(profile_data) // sample_size
        profile_samples = list(struct.unpack(f'<{profile_sample_count}{sample_format}', 
                                           profile_data))
        if bits_per_sample == 8:
            profile_samples = [s - zero_value for s in profile_samples]
        profile_segment = profile_samples[:window_size]
        if len(profile_segment) < window_size:
            profile_segment += [0] * (window_size - len(profile_segment))
        profile_fft = np.fft.fft(np.array(profile_segment) * window, n=window_size)
        noise_profile = np.abs(profile_fft) * reduction_factor
    
    # Process in overlapping windows
    for start in range(0, len(samples) - window_size + 1, hop_size):
        window_samples = samples[start:start + window_size]
        if len(window_samples) < window_size:
            window_samples += [0] * (window_size - len(window_samples))
        
        # Apply window
        windowed = np.array(window_samples) * window
        
        # FFT using NumPy
        freq_domain = np.fft.fft(windowed, n=window_size)
        
        # Spectral subtraction
        magnitudes = np.abs(freq_domain)
        phases = np.angle(freq_domain)
        new_magnitudes = np.maximum(0, magnitudes - noise_profile)
        freq_domain = new_magnitudes * np.exp(1j * phases)
        
        # IFFT using NumPy
        time_domain = np.fft.ifft(freq_domain, n=window_size).real
        
        # Overlap-add
        processed_samples[start:start + window_size] += time_domain * window
        window_count[start:start + window_size] += window
    
    # Normalize by window overlap
    final_samples = np.where(window_count > 1e-10, 
                           processed_samples / window_count, 
                           processed_samples)
    final_samples = np.clip(final_samples, -max_value - 1, max_value).astype(int)
    
    # Convert back to bytes
    if bits_per_sample == 24:
        new_data = bytearray(len(wav_data))
        for i, sample in enumerate(final_samples):
            if sample < 0:
                sample += 0x1000000
            byte_pos = i * 3
            new_data[byte_pos] = sample & 0xFF
            new_data[byte_pos + 1] = (sample >> 8) & 0xFF
            new_data[byte_pos + 2] = (sample >> 16) & 0xFF
        return bytes(new_data)
    else:
        if bits_per_sample == 8:
            final_samples = [s + zero_value for s in final_samples.tolist()]
        return struct.pack(format_str, *final_samples)
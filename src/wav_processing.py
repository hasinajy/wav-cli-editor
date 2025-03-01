"""
WAV Processing - Core audio processing functions
"""

import struct
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
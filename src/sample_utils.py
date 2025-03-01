"""
Sample Utilities - Helper functions for sample format and manipulation
"""

def get_sample_format_info(bits_per_sample):
    """
    Get sample format information based on bits per sample.
    
    Args:
        bits_per_sample (int): Bits per sample (8, 16, 24, 32)
        
    Returns:
        tuple: (sample_format, max_value, zero_value)
        
    Raises:
        ValueError: If bits per sample is unsupported
    """
    
    if bits_per_sample == 8:
        # 8-bit samples are unsigned
        return 'B', 255, 128  # unsigned char, max value, zero value
    elif bits_per_sample == 16:
        return 'h', 32767, 0  # signed short, max value, zero value
    elif bits_per_sample == 24:
        # Custom handling for 24-bit (3 bytes)
        return None, 8388607, 0  # No format char, max value, zero value
    elif bits_per_sample == 32:
        return 'i', 2147483647, 0  # signed int, max value, zero value
    else:
        raise ValueError(f"Unsupported bits per sample: {bits_per_sample}")
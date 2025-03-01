"""
WAV I/O - Functions for reading and writing WAV files
"""

import struct

def read_wav(file_path, verbose=False):
    """
    Read a WAV file and parse its headers and data
    
    Args:
        file_path (str): Path to the WAV file to read
        verbose (bool): Whether to print verbose output
        
    Returns:
        tuple: (sample_rate, num_channels, bits_per_sample, wav_data)
        
    Raises:
        ValueError: If the file is not a valid WAV file
    """
    def _print_verbose(message):
        if verbose:
            print(message)
    
    _print_verbose(f"Reading WAV file: {file_path}")
    
    with open(file_path, 'rb') as f:
        riff = f.read(4)
        if riff != b'RIFF':
            raise ValueError("Not a valid WAV file: RIFF header missing")
        
        _ = struct.unpack('<I', f.read(4))[0]
        
        wave = f.read(4)
        if wave != b'WAVE':
            raise ValueError("Not a valid WAV file: WAVE format missing")
        
        fmt = f.read(4)
        if fmt != b'fmt ':
            raise ValueError("Not a valid WAV file: fmt subchunk missing")
        
        subchunk1_size = struct.unpack('<I', f.read(4))[0]
        audio_format = struct.unpack('<H', f.read(2))[0]
        if audio_format != 1:
            raise ValueError("Only PCM WAV files are supported")
        
        num_channels = struct.unpack('<H', f.read(2))[0]
        sample_rate = struct.unpack('<I', f.read(4))[0]
        _ = struct.unpack('<I', f.read(4))[0]  # byte_rate
        _ = struct.unpack('<H', f.read(2))[0]  # block_align
        bits_per_sample = struct.unpack('<H', f.read(2))[0]
        
        if subchunk1_size > 16:
            f.read(subchunk1_size - 16)
        
        while True:
            chunk_id = f.read(4)
            if not chunk_id:
                raise ValueError("Data chunk not found in WAV file")
            if chunk_id == b'data':
                break
            chunk_size = struct.unpack('<I', f.read(4))[0]
            f.read(chunk_size)
        
        data_size = struct.unpack('<I', f.read(4))[0]
        wav_data = f.read(data_size)
        
        _print_verbose(f"Sample rate: {sample_rate} Hz")
        _print_verbose(f"Channels: {num_channels}")
        _print_verbose(f"Bits per sample: {bits_per_sample}")
        _print_verbose(f"Data size: {data_size} bytes")
        
        if num_channels not in (1, 2):
            raise ValueError(f"Unsupported number of channels: {num_channels}")
        if bits_per_sample not in (8, 16, 24, 32):
            raise ValueError(f"Unsupported bits per sample: {bits_per_sample}")
        
        return sample_rate, num_channels, bits_per_sample, wav_data


def write_wav(output_path, sample_rate, num_channels, bits_per_sample, wav_data, verbose=False):
    """
    Write audio data to a new WAV file
    
    Args:
        output_path (str): Path to write the WAV file
        sample_rate (int): Sample rate in Hz
        num_channels (int): Number of channels (1 or 2)
        bits_per_sample (int): Bits per sample (8, 16, 24, 32)
        wav_data (bytes): Raw audio data
        verbose (bool): Whether to print verbose output
        
    Returns:
        str: Path to the written file
        
    Raises:
        ValueError: If no WAV data is provided
    """
    def _print_verbose(message):
        if verbose:
            print(message)
    
    if wav_data is None:
        raise ValueError("No WAV data provided")
    
    _print_verbose(f"Writing WAV file: {output_path}")
    
    with open(output_path, 'wb') as f:
        f.write(b'RIFF')
        file_size = 36 + len(wav_data)
        f.write(struct.pack('<I', file_size))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))
        f.write(struct.pack('<H', 1))  # PCM format
        f.write(struct.pack('<H', num_channels))
        f.write(struct.pack('<I', sample_rate))
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        f.write(struct.pack('<I', byte_rate))
        block_align = num_channels * bits_per_sample // 8
        f.write(struct.pack('<H', block_align))
        f.write(struct.pack('<H', bits_per_sample))
        f.write(b'data')
        f.write(struct.pack('<I', len(wav_data)))
        f.write(wav_data)
    
    _print_verbose("Write complete")
    return output_path
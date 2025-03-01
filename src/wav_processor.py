"""
WAV Processor - Core audio processing functions for the WAV Editor
"""

import struct


class WAVProcessor:
    """
    A class for processing WAV audio files without external libraries.
    Supports both mono and stereo WAV files.
    """

    def __init__(self, verbose=False):
        """
        Initialize the WAV processor
        
        Args:
            verbose (bool): Whether to print verbose output
        """
        self.verbose = verbose
        self.wav_data = None
        self.sample_rate = None
        self.num_channels = None
        self.bits_per_sample = None
        self.data_size = None
        
    def _print_verbose(self, message):
        """Print a message if verbose mode is enabled"""
        if self.verbose:
            print(message)

    def read_wav(self, file_path):
        """
        Read a WAV file and parse its headers and data
        
        Args:
            file_path (str): Path to the WAV file to read
            
        Returns:
            tuple: Audio parameters and raw sample data
            
        Raises:
            ValueError: If the file is not a valid WAV file
        """
        self._print_verbose(f"Reading WAV file: {file_path}")
        
        with open(file_path, 'rb') as f:
            # Read RIFF header
            riff = f.read(4)
            if riff != b'RIFF':
                raise ValueError("Not a valid WAV file: RIFF header missing")
            
            # Read file size (minus 8 bytes for the RIFF and size fields)
            # We read but don't need to use this value as we'll read the entire file
            _ = struct.unpack('<I', f.read(4))[0]  # Removed unused chunk_size variable
            
            # Read WAVE format
            wave = f.read(4)
            if wave != b'WAVE':
                raise ValueError("Not a valid WAV file: WAVE format missing")
            
            # Read fmt subchunk
            fmt = f.read(4)
            if fmt != b'fmt ':
                raise ValueError("Not a valid WAV file: fmt subchunk missing")
            
            # Read fmt chunk size
            subchunk1_size = struct.unpack('<I', f.read(4))[0]
            
            # Read audio format (1 is PCM)
            audio_format = struct.unpack('<H', f.read(2))[0]
            if audio_format != 1:
                raise ValueError("Only PCM WAV files are supported")
            
            # Read number of channels
            self.num_channels = struct.unpack('<H', f.read(2))[0]
            
            # Read sample rate
            self.sample_rate = struct.unpack('<I', f.read(4))[0]
            
            # Read byte rate - skipping as it's not used
            _ = struct.unpack('<I', f.read(4))[0]  # Removed unused byte_rate variable
            
            # Read block align - skipping as it's not used
            _ = struct.unpack('<H', f.read(2))[0]  # Removed unused block_align variable
            
            # Read bits per sample
            self.bits_per_sample = struct.unpack('<H', f.read(2))[0]
            
            # Skip any extra parameters in the fmt chunk
            if subchunk1_size > 16:
                f.read(subchunk1_size - 16)
            
            # Find the data chunk (skip any non-data chunks)
            while True:
                chunk_id = f.read(4)
                
                if not chunk_id:
                    raise ValueError("Data chunk not found in WAV file")
                
                if chunk_id == b'data':
                    break
                
                # Skip this chunk
                chunk_size = struct.unpack('<I', f.read(4))[0]
                f.read(chunk_size)
            
            # Read data chunk size
            self.data_size = struct.unpack('<I', f.read(4))[0]
            
            # Read the actual audio data
            self.wav_data = f.read(self.data_size)
            
            self._print_verbose(f"Sample rate: {self.sample_rate} Hz")
            self._print_verbose(f"Channels: {self.num_channels}")
            self._print_verbose(f"Bits per sample: {self.bits_per_sample}")
            self._print_verbose(f"Data size: {self.data_size} bytes")
            
            if self.num_channels not in (1, 2):
                raise ValueError(f"Unsupported number of channels: {self.num_channels}")
            
            if self.bits_per_sample not in (8, 16, 24, 32):
                raise ValueError(f"Unsupported bits per sample: {self.bits_per_sample}")
            
            return (self.sample_rate, self.num_channels, self.bits_per_sample, self.wav_data)

    def _get_sample_format_info(self):
        """
        Get sample format information based on bits per sample.
        
        Returns:
            tuple: (sample_format, max_value, zero_value)
        """
        if self.bits_per_sample == 8:
            # 8-bit samples are unsigned
            return 'B', 255, 128  # unsigned char, max value, zero value
        elif self.bits_per_sample == 16:
            return 'h', 32767, 0  # signed short, max value, zero value
        elif self.bits_per_sample == 24:
            # Custom handling for 24-bit (3 bytes)
            return None, 8388607, 0  # No format char, max value, zero value
        elif self.bits_per_sample == 32:
            return 'i', 2147483647, 0  # signed int, max value, zero value
        else:
            raise ValueError(f"Unsupported bits per sample: {self.bits_per_sample}")

    def _process_standard_samples(self, gain):
        """
        Process 8, 16, or 32-bit samples with struct.
        
        Args:
            gain (float): The gain factor to apply
            
        Returns:
            bytes: Processed audio data
        """
        sample_format, max_value, zero_value = self._get_sample_format_info()
        sample_size = self.bits_per_sample // 8
        sample_count = len(self.wav_data) // sample_size
        
        # Unpack all samples
        format_str = '<' + sample_format * sample_count
        samples = list(struct.unpack(format_str, self.wav_data))
        
        # Apply gain and clip if necessary
        for i in range(sample_count):
            # Convert to signed value if needed
            if self.bits_per_sample == 8:
                sample_value = samples[i] - zero_value
            else:
                sample_value = samples[i]
            
            # Apply gain
            sample_value = int(sample_value * gain)
            
            # Clip to prevent overflow
            min_value = -max_value if zero_value == 0 else -zero_value
            sample_value = max(min_value, min(max_value, sample_value))
            
            # Convert back to unsigned for 8-bit
            if self.bits_per_sample == 8:
                samples[i] = sample_value + zero_value
            else:
                samples[i] = sample_value
        
        # Pack the modified samples back into bytes
        return struct.pack(format_str, *samples)

    def _process_24bit_samples(self, gain):
        """
        Process 24-bit samples.
        
        Args:
            gain (float): The gain factor to apply
            
        Returns:
            bytes: Processed audio data
        """
        _, max_value, _ = self._get_sample_format_info()
        sample_size = 3  # 24 bits = 3 bytes
        sample_count = len(self.wav_data) // sample_size
        new_data = bytearray(len(self.wav_data))
        
        for i in range(sample_count):
            # Extract 3 bytes from the original data
            byte_pos = i * sample_size
            b1 = self.wav_data[byte_pos]
            b2 = self.wav_data[byte_pos + 1]
            b3 = self.wav_data[byte_pos + 2]
            
            # Convert to a signed 24-bit integer (little-endian)
            sample_value = b1 | (b2 << 8) | (b3 << 16)
            if sample_value & 0x800000:  # If sign bit is set
                sample_value = sample_value - 0x1000000  # Convert to negative
            
            # Apply gain
            sample_value = int(sample_value * gain)
            
            # Clip to prevent overflow
            sample_value = max(-max_value, min(max_value, sample_value))
            
            # Convert back to 3 bytes (and handle negative values)
            if sample_value < 0:
                sample_value = sample_value + 0x1000000  # Convert from negative
            
            new_data[byte_pos] = sample_value & 0xFF
            new_data[byte_pos + 1] = (sample_value >> 8) & 0xFF
            new_data[byte_pos + 2] = (sample_value >> 16) & 0xFF
        
        return bytes(new_data)

    def amplify(self, gain):
        """
        Amplify the audio by the specified gain factor
        
        Args:
            gain (float): The gain factor to apply
            
        Raises:
            ValueError: If gain is negative or if no WAV data is loaded
        """
        if gain < 0:
            raise ValueError("Gain factor cannot be negative")
            
        if self.wav_data is None:
            raise ValueError("No WAV data loaded. Call read_wav first.")
        
        self._print_verbose(f"Amplifying audio with gain factor: {gain}")
        
        # Process samples based on bit depth
        if self.bits_per_sample == 24:
            self.wav_data = self._process_24bit_samples(gain)
        else:
            self.wav_data = self._process_standard_samples(gain)
        
        self._print_verbose("Amplification complete")

    def write_wav(self, output_path):
        """
        Write the processed audio data to a new WAV file
        
        Args:
            output_path (str): Path to write the WAV file
            
        Raises:
            ValueError: If no WAV data is loaded
        """
        if self.wav_data is None:
            raise ValueError("No WAV data loaded. Call read_wav first.")
        
        self._print_verbose(f"Writing WAV file: {output_path}")
        
        with open(output_path, 'wb') as f:
            # Write RIFF header
            f.write(b'RIFF')
            
            # Write file size (minus 8 bytes for the RIFF and size fields)
            file_size = 36 + len(self.wav_data)  # 36 = size of header
            f.write(struct.pack('<I', file_size))
            
            # Write WAVE format
            f.write(b'WAVE')
            
            # Write fmt subchunk
            f.write(b'fmt ')
            
            # Write fmt chunk size (16 for PCM)
            f.write(struct.pack('<I', 16))
            
            # Write audio format (1 for PCM)
            f.write(struct.pack('<H', 1))
            
            # Write number of channels
            f.write(struct.pack('<H', self.num_channels))
            
            # Write sample rate
            f.write(struct.pack('<I', self.sample_rate))
            
            # Calculate and write byte rate
            byte_rate = self.sample_rate * self.num_channels * self.bits_per_sample // 8
            f.write(struct.pack('<I', byte_rate))
            
            # Calculate and write block align
            block_align = self.num_channels * self.bits_per_sample // 8
            f.write(struct.pack('<H', block_align))
            
            # Write bits per sample
            f.write(struct.pack('<H', self.bits_per_sample))
            
            # Write data subchunk
            f.write(b'data')
            
            # Write data size
            f.write(struct.pack('<I', len(self.wav_data)))
            
            # Write the audio data
            f.write(self.wav_data)
            
        self._print_verbose("Write complete")
        
        return output_path
"""
WAV Processor - Main class for WAV audio processing
"""

from wav_io import read_wav, write_wav
from wav_processing import process_standard_samples, process_24bit_samples

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
    
    def _print_verbose(self, message):
        """Print a message if verbose mode is enabled"""
        
        if self.verbose:
            print(message)
    
    def read_wav(self, file_path):
        """
        Read a WAV file and store its parameters and data
        
        Args:
            file_path (str): Path to the WAV file
        """
        
        self.sample_rate, self.num_channels, self.bits_per_sample, self.wav_data = read_wav(file_path, self.verbose)
    
    def amplify(self, gain):
        """
        Amplify the audio by the specified gain factor
        
        Args:
            gain (float): The gain factor to apply
            
        Raises:
            ValueError: If gain is negative or no WAV data loaded
        """
        
        if gain < 0:
            raise ValueError("Gain factor cannot be negative")
        
        if self.wav_data is None:
            raise ValueError("No WAV data loaded. Call read_wav first.")
        
        self._print_verbose(f"Amplifying audio with gain factor: {gain}")
        
        if self.bits_per_sample == 24:
            self.wav_data = process_24bit_samples(self.wav_data, gain=gain)
        else:
            self.wav_data = process_standard_samples(self.wav_data, self.bits_per_sample, gain=gain)
        
        self._print_verbose("Amplification complete")
    
    def anti_distortion(self, threshold):
        """
        Apply anti-distortion to the audio by soft clipping above a threshold
        
        Args:
            threshold (float): Normalized threshold (0.0-1.0) for clipping
            
        Raises:
            ValueError: If threshold is not between 0.0 and 1.0 or no WAV data loaded
        """
        
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        if self.wav_data is None:
            raise ValueError("No WAV data loaded. Call read_wav first.")
        
        self._print_verbose(f"Applying anti-distortion with threshold: {threshold}")
        
        if self.bits_per_sample == 24:
            self.wav_data = process_24bit_samples(self.wav_data, threshold=threshold)
        else:
            self.wav_data = process_standard_samples(self.wav_data, self.bits_per_sample, threshold=threshold)
        
        self._print_verbose("Anti-distortion complete")
    
    def write_wav(self, output_path):
        """
        Write the processed audio data to a new WAV file
        
        Args:
            output_path (str): Path to write the WAV file
        """
       
        return write_wav(output_path, self.sample_rate, self.num_channels, self.bits_per_sample, self.wav_data, self.verbose)
"""
WAV Editor - A command-line tool for audio processing
"""

import argparse
import os
import sys
from wav_processor import WAVProcessor

def validate_file_path(path, should_exist=True):
    """
    Validates if a file path exists or can be created.
    
    Args:
        path (str): The file path to validate
        should_exist (bool): Whether the file should already exist
        
    Returns:
        str: The validated file path
        
    Raises:
        argparse.ArgumentTypeError: If the path is invalid
    """
    if should_exist and not os.path.isfile(path):
        raise argparse.ArgumentTypeError(f"The file '{path}' does not exist")
    
    if not should_exist:
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            raise argparse.ArgumentTypeError(f"The directory '{directory}' does not exist")
    
    return path

def validate_input_file(path):
    """Validates that the input file exists and has a .wav extension"""
    path = validate_file_path(path, should_exist=True)
    if not path.lower().endswith('.wav'):
        raise argparse.ArgumentTypeError("Input file must have a .wav extension")
    return path

def validate_output_file(path):
    """Validates that the output path is valid and has a .wav extension"""
    path = validate_file_path(path, should_exist=False)
    if not path.lower().endswith('.wav'):
        raise argparse.ArgumentTypeError("Output file must have a .wav extension")
    return path

def process_audio(args):
    """Process the audio based on the specified action"""
    processor = WAVProcessor(verbose=args.verbose)
    
    # Read the input WAV file
    processor.read_wav(args.path)
    
    # Process based on action
    if args.action == "amplify":
        processor.amplify(args.gain)
    # Add other actions (anti-distortion, noise-removal) here when implemented
    
    # Write the processed audio
    processor.write_wav(args.output)

def main():
    """Main function for the WAV editor CLI"""
    parser = argparse.ArgumentParser(
        description="WAV Editor - A command-line tool for audio processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Amplify a WAV file
  ./wav_editor.py -p input.wav -o output.wav --action amplify --gain 2.0
  
  # Remove noise from a WAV file
  ./wav_editor.py -p input.wav -o output.wav --action noise-removal --strength medium
  
  # Apply anti-distortion to a WAV file
  ./wav_editor.py -p input.wav -o output.wav --action anti-distortion --threshold 0.8
        """
    )
    
    # Required arguments
    parser.add_argument("-p", "--path", type=validate_input_file, required=True,
                        help="Path to the input WAV file")
    parser.add_argument("-o", "--output", type=validate_output_file, required=True,
                        help="Path to save the processed WAV file")
    
    # Action argument
    parser.add_argument("--action", type=str, required=True,
                        choices=["amplify", "anti-distortion", "noise-removal"],
                        help="Processing action to apply to the WAV file")
    
    # Action-specific arguments
    amplify_group = parser.add_argument_group("Amplify options")
    amplify_group.add_argument("--gain", type=float, default=2.0,
                              help="Gain factor for amplification (default: 2.0)")
    
    anti_distortion_group = parser.add_argument_group("Anti-distortion options")
    anti_distortion_group.add_argument("--threshold", type=float, default=0.8,
                                      help="Threshold for anti-distortion (0.0-1.0, default: 0.8)")
    
    noise_removal_group = parser.add_argument_group("Noise removal options")
    noise_removal_group.add_argument("--strength", type=str, default="medium",
                                    choices=["low", "medium", "high"],
                                    help="Strength of noise removal (default: medium)")
    noise_removal_group.add_argument("--profile", type=str,
                                    help="Path to a noise profile file")
    
    # Additional options
    parser.add_argument("--verbose", action="store_true", 
                        help="Enable verbose output")
    parser.add_argument("--version", action="version", version="WAV Editor v1.0.0",
                        help="Show program's version number and exit")
    
    args = parser.parse_args()
    
    print(f"Action: {args.action}")
    print(f"Input file: {args.path}")
    print(f"Output file: {args.output}")
    
    # Action-specific parameter reporting
    if args.action == "amplify":
        print(f"Gain: {args.gain}")
    elif args.action == "anti-distortion":
        print(f"Threshold: {args.threshold}")
    elif args.action == "noise-removal":
        print(f"Strength: {args.strength}")
        if args.profile:
            print(f"Noise profile: {args.profile}")
    
    # Process the audio
    process_audio(args)
    
    print("Processing complete!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
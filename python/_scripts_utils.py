#!/usr/bin/env python3
"""
_scripts_utils.py - Project context utilities for BWV scripts

This module provides utilities for BWV musical score processing scripts,
handling file naming conventions and argument parsing patterns.

The only interface with the build system is the PROJECT_NAME environment variable.
"""

import os
import sys
import argparse

def get_io_files(description, input_pattern, output_pattern):
    """
    Simple 1 input → 1 output file resolver.
    
    Args:
        description: Script description for help text
        input_pattern: Input file pattern with {project} placeholder
        output_pattern: Output file pattern with {project} placeholder
    
    Returns:
        tuple: (input_file, output_file) as strings
    """
    project_name = os.getenv("PROJECT_NAME")
    
    if project_name:
        # Build system mode - use project conventions
        return (
            input_pattern.format(project=project_name),
            output_pattern.format(project=project_name)
        )
    else:
        # Standalone mode - require explicit arguments
        if len(sys.argv) != 3:
            print(f"Usage: python {sys.argv[0]} <input> <output>")
            print(f"Description: {description}")
            print("Or run from build system with PROJECT_NAME environment variable")
            sys.exit(1)
        return sys.argv[1], sys.argv[2]

def get_project_name():
    """Get project name for multi-input scripts like align_pitch_by_geometry_simplified.py"""
    return os.getenv("PROJECT_NAME", "bwv1006")

def setup_project_context(script_purpose, input_pattern=None, output_pattern=None, extra_args=None):
    """
    Setup project context and argument parsing for BWV scripts.
    
    Relies on PROJECT_NAME environment variable set by build system.
    If not set, requires explicit file arguments.
    
    Args:
        script_purpose: Description for help text
        input_pattern: Format string for input file (e.g., "{project}_input.svg") or None
        output_pattern: Format string for output file (e.g., "{project}_output.svg") or None
        extra_args: List of additional argument definitions [(name, kwargs), ...]
    
    Returns:
        argparse.Namespace: Parsed arguments with input/output paths
    """
    project_name = os.getenv("PROJECT_NAME")
    
    parser = argparse.ArgumentParser(description=script_purpose)
    
    # Handle input file argument
    if input_pattern:
        if project_name:
            input_default = input_pattern.format(project=project_name)
            input_required = False
        else:
            input_default = None
            input_required = True
        
        parser.add_argument('--input', default=input_default, required=input_required,
                           help='Input file path')
    
    # Handle output file argument  
    if output_pattern:
        if project_name:
            output_default = output_pattern.format(project=project_name)
            output_required = False
        else:
            output_default = None
            output_required = True
            
        parser.add_argument('--output', default=output_default, required=output_required,
                           help='Output file path')
    
    # Handle positional arguments (for scripts that take them directly)
    if not input_pattern and not output_pattern:
        parser.add_argument('input_file', nargs='?', help='Input file')
        parser.add_argument('output_file', nargs='?', help='Output file')
    
    # Add any extra arguments
    if extra_args:
        for arg_name, arg_kwargs in extra_args:
            parser.add_argument(arg_name, **arg_kwargs)
    
    args = parser.parse_args()
    
    # For positional args, validate we have what we need
    if not input_pattern and not output_pattern:
        if not project_name and (not args.input_file or not args.output_file):
            parser.error("When PROJECT_NAME is not set, both input_file and output_file are required")
        elif project_name and not args.input_file:
            # Use project context to generate default positional args
            setattr(args, 'input_file', input_pattern.format(project=project_name) if input_pattern else None)
            setattr(args, 'output_file', output_pattern.format(project=project_name) if output_pattern else None)
    
    return args


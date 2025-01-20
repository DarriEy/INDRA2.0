import yaml # type: ignore
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import anthropic # type: ignore
import os
import time
from datetime import datetime

class AnthropicAPI:
    """Wrapper for Anthropic's Claude API providing controlled access to language model capabilities."""
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def generate_response(self, prompt: str, system_message: str, max_tokens: int = 1500) -> str:
        """Generate response using Anthropic's Claude model."""
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=max_tokens,
                temperature=0.7,  # Slightly higher temperature for more dynamic responses
                system=system_message,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Error generating response: {e}")
            return ""

class INDRASingleAgent:
    """
    Single agent version of INDRA focused on conversational configuration generation.
    
    This version provides a more natural dialogue interface for generating CONFLUENCE
    configurations while maintaining compatibility with the CONFLUENCE format.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize INDRA with API key from environment or direct input."""
        if not api_key:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not found in environment variables or constructor. "
                    "Please provide an API key."
                )
        
        self.api = AnthropicAPI(api_key)
        self.system_message = """You are INDRA (Intelligent Network for Dynamic River Analysis), 
        a hydrological modeling expert specializing in configuring CONFLUENCE models. You engage
        in natural conversation to understand watershed modeling needs and generate appropriate 
        configurations. You should:
        1. Ask relevant questions about the watershed and modeling requirements
        2. Provide clear explanations for your configuration choices
        3. Generate configurations compatible with the CONFLUENCE format
        4. Maintain a helpful and educational tone while ensuring technical accuracy"""
        
        self.conversation_history = []
        
    def start_configuration_dialogue(self) -> Tuple[Dict[str, Any], str]:
        """
        Main entry point for configuration conversation.
        
        Returns:
            Tuple containing:
            - Configuration dictionary
            - Justification string explaining configuration choices
        """
        print("Starting INDRA configuration dialogue...")
        
        # Get watershed name
        watershed_name = input("What is the name of the watershed you want to model? ").strip()
        
        # Initialize conversation with watershed context
        prompt = f"""I'd like to help you configure a CONFLUENCE model for the {watershed_name} watershed. 
        First, I need to understand some basic information about your modeling goals and the watershed characteristics. 
        What is the primary purpose of this modeling exercise?"""
        
        print("\nINDRA: " + prompt)
        
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'done']:
                break
            
            # Add user input to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Generate response considering conversation history
            response = self._generate_response(user_input)
            print("\nINDRA: " + response)
            
            # Add response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Check if we have enough information for configuration
            if self._has_sufficient_information():
                if input("\nI believe I have enough information to generate a configuration. Would you like to proceed? (y/n): ").lower() == 'y':
                    break
        
        # Generate configuration and justification
        config = self._generate_config(watershed_name)
        justification = self._generate_justification(config)
        
        # Save outputs
        self._save_outputs(config, justification, watershed_name)
        
        return config, justification
    
    def _generate_response(self, user_input: str) -> str:
        """Generate contextual response based on conversation history."""
        # Construct prompt with conversation history
        history_text = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'INDRA'}: {msg['content']}"
            for msg in self.conversation_history[-4:]  # Include last 4 messages for context
        ])
        
        prompt = f"""Conversation history:
        {history_text}
        
        User: {user_input}
        
        Based on this conversation about watershed modeling, provide a helpful response that either:
        1. Asks for clarifying information about the watershed or modeling needs
        2. Suggests specific configuration options with explanations
        3. Addresses any concerns or questions raised
        
        Keep responses focused on gathering necessary information for CONFLUENCE configuration."""
        
        return self.api.generate_response(prompt, self.system_message)
    
    def _has_sufficient_information(self) -> bool:
        """Check if we have enough information to generate configuration."""
        required_topics = [
            'watershed_characteristics',
            'modeling_purpose',
            'temporal_scale',
            'spatial_resolution'
        ]
        
        # Analyze conversation history to check for required information
        conversation_text = " ".join([msg["content"] for msg in self.conversation_history])
        
        prompt = f"""Based on the following conversation, determine if we have sufficient information 
        about: {', '.join(required_topics)}. Respond with only YES or NO.
        
        Conversation:
        {conversation_text}"""
        
        response = self.api.generate_response(prompt, self.system_message)
        return response.strip().upper() == "YES"
    
    def _create_config_from_template(self, template_path: Path, output_path: Path, watershed_name: str, config_updates: Dict[str, Any]):
        """
        Generate configuration file from template with conversation-based updates.
        
        Args:
            template_path (Path): Path to template configuration file
            output_path (Path): Where to save the new configuration
            watershed_name (str): Name of watershed being modeled
            config_updates (Dict[str, Any]): Settings to update based on conversation
        """
        if not template_path.exists():
            raise FileNotFoundError(f"Configuration template not found at: {template_path}")
        
        # Read template file preserving all lines
        with open(template_path, 'r') as f:
            template_lines = f.readlines()
        
        # Add watershed name to updates
        config_updates['DOMAIN_NAME'] = watershed_name
        
        # These are the settings we allow to be modified through conversation
        MODIFIABLE_SETTINGS = {
            'HYDROLOGICAL_MODEL',
            'ROUTING_MODEL',
            'DOMAIN_DEFINITION_METHOD',
            'DOMAIN_DISCRETIZATION',
            'FORCING_DATASET',
            'ELEVATION_BAND_SIZE',
            'MIN_HRU_SIZE',
            'POUR_POINT_COORDS',
            'BOUNDING_BOX_COORDS',
            'EXPERIMENT_TIME_START',
            'EXPERIMENT_TIME_END',
            'OPTIMIZATION_METRIC',
            'NUMBER_OF_ITERATIONS',
            'PARAMS_TO_CALIBRATE'
        }
        
        # Process template line by line
        with open(output_path, 'w') as f:
            for line in template_lines:
                # Preserve comment lines and section headers
                if line.strip().startswith('#') or line.strip().startswith('### ==='):
                    f.write(line)
                    continue
                
                # Process configuration lines
                if ':' in line:
                    key = line.split(':')[0].strip()
                    if key in MODIFIABLE_SETTINGS and key in config_updates:
                        # Preserve any inline comments
                        comment = line.split('#')[1].strip() if '#' in line else ''
                        value = config_updates[key]
                        
                        # Handle different value types
                        if isinstance(value, bool):
                            value_str = str(value)
                        elif isinstance(value, str) and ' ' in value:
                            value_str = f"'{value}'"
                        else:
                            value_str = str(value)
                        
                        new_line = f"{key}: {value_str}"
                        if comment:
                            new_line += f"  # {comment}"
                        f.write(new_line + '\n')
                    else:
                        # Keep original line for non-modified settings
                        f.write(line)
                else:
                    f.write(line)

    def _extract_config_from_conversation(self) -> Dict[str, Any]:
        """
        Extract configuration settings from conversation history.
        
        Returns:
            Dict[str, Any]: Configuration updates based on conversation
        """
        conversation_text = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in self.conversation_history
        ])
        
        prompt = f"""Based on our conversation about the watershed modeling needs, 
        determine appropriate values for the following CONFLUENCE configuration parameters.
        Only include parameters that were directly discussed or can be confidently inferred.
        
        YOU MUST FOLLOW THE EXACT FORMAT OF THE CONFLUENCE CONFIGURATION FILE.
        Each parameter must exactly match one of the available options.
        
        Parameters to extract (only include if discussed):
        
        1. HYDROLOGICAL_MODEL: Must be one of: SUMMA, FLASH, FUSE, GR, HYPE, MESH
        2. ROUTING_MODEL: Must be one of: mizuRoute
        3. DOMAIN_DEFINITION_METHOD: Must be one of: delineate, subset, lumped
        4. DOMAIN_DISCRETIZATION: Must be one of: elevation, soilclass, landclass, radiation, GRUs, combined
        5. FORCING_DATASET: Must be one of: ERA5, RDRS, CARRA, GWF-I, GWF-II, DayMet, NEX-GDDP
        6. ELEVATION_BAND_SIZE: Integer value in meters (if using elevation discretization)
        7. MIN_HRU_SIZE: Integer value in km²
        8. EXPERIMENT_TIME_START: Format YYYY-MM-DD HH:MM
        9. EXPERIMENT_TIME_END: Format YYYY-MM-DD HH:MM
        10. OPTIMIZATION_METRIC: Must be one of: RMSE, NSE, KGE, KGEp, MAE

        Conversation:
        {conversation_text}
        
        Return ONLY a valid Python dictionary containing EXACTLY the discussed parameters:
        {
            "PARAMETER": "value",  # Only include if explicitly discussed or clearly implied
        }
        
        Example:
        {
            "HYDROLOGICAL_MODEL": "SUMMA",
            "FORCING_DATASET": "ERA5",
            "EXPERIMENT_TIME_START": "2010-01-01 00:00",
            "EXPERIMENT_TIME_END": "2020-12-31 23:00"
        }
        """
        
        response = self.api.generate_response(prompt, self.system_message)
        
        try:
            # Extract dictionary from response
            dict_text = response.split('{')[1].split('}')[0]
            config_dict = eval("{" + dict_text + "}")
            
            # Validate the returned configuration
            return self._validate_config_values(config_dict)
        except Exception as e:
            print(f"Error parsing configuration from conversation: {e}")
            return {}

    def _validate_config_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration values against allowed options."""
        
        VALID_OPTIONS = {
            'HYDROLOGICAL_MODEL': {'SUMMA', 'FLASH', 'FUSE', 'GR', 'HYPE', 'MESH'},
            'ROUTING_MODEL': {'mizuRoute'},
            'DOMAIN_DEFINITION_METHOD': {'delineate', 'subset', 'lumped'},
            'DOMAIN_DISCRETIZATION': {'elevation', 'soilclass', 'landclass', 'radiation', 'GRUs', 'combined'},
            'FORCING_DATASET': {'ERA5', 'RDRS', 'CARRA', 'GWF-I', 'GWF-II', 'DayMet', 'NEX-GDDP'},
            'OPTIMIZATION_METRIC': {'RMSE', 'NSE', 'KGE', 'KGEp', 'MAE'}
        }
        
        validated_config = {}
        
        for key, value in config.items():
            # Check if parameter is in validation set
            if key in VALID_OPTIONS:
                if value in VALID_OPTIONS[key]:
                    validated_config[key] = value
                else:
                    print(f"Warning: Invalid value '{value}' for {key}. Must be one of: {VALID_OPTIONS[key]}")
            # Validate time formats
            elif key in {'EXPERIMENT_TIME_START', 'EXPERIMENT_TIME_END'}:
                try:
                    datetime.strptime(value, '%Y-%m-%d %H:%M')
                    validated_config[key] = value
                except ValueError:
                    print(f"Warning: Invalid time format for {key}. Must be YYYY-MM-DD HH:MM")
            # Validate numeric values
            elif key in {'ELEVATION_BAND_SIZE', 'MIN_HRU_SIZE'}:
                try:
                    num_value = int(value)
                    if num_value > 0:
                        validated_config[key] = num_value
                    else:
                        print(f"Warning: {key} must be positive")
                except ValueError:
                    print(f"Warning: {key} must be an integer")
            else:
                validated_config[key] = value
        
        return validated_config

    def _save_configuration(self, watershed_name: str, config_updates: Dict[str, Any]) -> Path:
        """
        Save configuration using the CONFLUENCE template format.
        
        Args:
            watershed_name (str): Name of the watershed
            config_updates (Dict[str, Any]): Configuration updates from conversation
            
        Returns:
            Path: Path to saved configuration file
        """
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"indra_outputs_{watershed_name}_{timestamp}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define input and output paths
        template_path = Path("config_template.yaml")
        config_path = output_dir / f"config_{watershed_name}.yaml"
        
        if not template_path.exists():
            raise FileNotFoundError(
                f"CONFLUENCE template not found at {template_path}. "
                "Please ensure the template file is in the current directory."
            )
        
        # Read template and update with new values
        with open(template_path, 'r') as f:
            template_lines = f.readlines()
        
        # Add watershed name to updates
        config_updates['DOMAIN_NAME'] = watershed_name
        
        # Write updated config file
        with open(config_path, 'w') as f:
            current_section = None
            
            for line in template_lines:
                # Preserve section headers and comments
                if line.strip().startswith('#') or line.strip().startswith('### ==='):
                    f.write(line)
                    continue
                    
                # Process configuration lines
                if ':' in line:
                    key = line.split(':')[0].strip()
                    
                    if key in config_updates:
                        # Get value and preserve any inline comments
                        value = config_updates[key]
                        comment = line.split('#')[1].strip() if '#' in line else ''
                        
                        # Format value based on type
                        if isinstance(value, bool):
                            value_str = str(value)
                        elif isinstance(value, str) and ' ' in value:
                            value_str = f"'{value}'"
                        else:
                            value_str = str(value)
                        
                        # Write updated line preserving format
                        new_line = f"{key}: {value_str}"
                        if comment:
                            new_line += f"  # {comment}"
                        f.write(new_line + '\n')
                    else:
                        # Keep original line for non-updated settings
                        f.write(line)
                else:
                    f.write(line)
        
        print(f"\nConfiguration saved to: {config_path}")
        return config_path

    def _generate_config(self, watershed_name: str) -> Dict[str, Any]:
        """Generate CONFLUENCE configuration from conversation history."""
        # Extract configuration updates from conversation
        config_updates = self._extract_config_from_conversation()
        
        # Save configuration using template
        config_path = self._save_configuration(watershed_name, config_updates)
        
        # Read and return complete configuration
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _generate_justification(self, config: Dict[str, Any]) -> str:
        """Generate justification document for configuration choices."""
        prompt = f"""Generate a detailed justification document for the following CONFLUENCE configuration:
        
        Configuration:
        {yaml.dump(config)}
        
        Include:
        1. Overview of the watershed and modeling goals
        2. Explanation of key configuration choices
        3. Expected benefits and potential limitations
        4. Recommendations for model evaluation
        
        Format as a clear, professional document."""
        
        return self.api.generate_response(prompt, self.system_message)
    
    def _save_outputs(self, config: Dict[str, Any], justification: str, watershed_name: str):
        """Save configuration and justification files."""
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"indra_outputs_{watershed_name}_{timestamp}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        config_file = output_dir / f"config_{watershed_name}.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f, sort_keys=False)
        
        # Save justification
        justification_file = output_dir / f"justification_{watershed_name}.txt"
        with open(justification_file, 'w') as f:
            f.write(justification)
        
        print(f"\nOutputs saved to: {output_dir}")
        print(f"Configuration file: {config_file}")
        print(f"Justification file: {justification_file}")

if __name__ == "__main__":
    try:
        indra = INDRASingleAgent()
        config, justification = indra.start_configuration_dialogue()
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTo set up your API key in the system environment:")
        print("\nFor Unix-like systems (Linux/Mac):")
        print("1. Add this line to your ~/.bashrc or ~/.zshrc:")
        print('   export ANTHROPIC_API_KEY="your-api-key-here"')
        print("2. Run: source ~/.bashrc (or source ~/.zshrc)")
        print("\nFor Windows:")
        print("1. Open System Properties -> Advanced -> Environment Variables")
        print("2. Add a new User Variable:")
        print("   Name: ANTHROPIC_API_KEY")
        print("   Value: your-api-key")
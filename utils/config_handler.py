from typing import Dict, Any, Optional, List
import logging
from pathlib import Path
import yaml # type: ignore
import json
import shutil
from datetime import datetime

from utils.exceptions import ConfigError # type: ignore

class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class ConfigHandler:
    """Handles CONFLUENCE configuration management with template support."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.config_backup_dir = Path("config_backups")
        self.config_backup_dir.mkdir(exist_ok=True)
        
        # Load both raw and parsed template
        self.template_content = self._load_template_content()
        self.template_dict = yaml.safe_load(self.template_content)
        
        # Fields that can be modified by expert system
        self.modifiable_fields = {
            'HYDROLOGICAL_MODEL',
            'DOMAIN_DEFINITION_METHOD',
            'ROUTING_MODEL',
            'FORCING_DATASET',
            'DOMAIN_DISCRETIZATION',
            'ELEVATION_BAND_SIZE',
            'MIN_HRU_SIZE'
        }

    def _load_template_content(self) -> str:
        """Load the raw template content."""
        possible_paths = [
            Path(__file__).parent.parent / '0_config_files' / 'config_template.yaml',
            Path.cwd() / '0_config_files' / 'config_template.yaml',
            Path.cwd() / 'config_template.yaml'
        ]
        
        template_path = None
        for path in possible_paths:
            if path.exists():
                template_path = path
                break
        
        if not template_path:
            raise FileNotFoundError(
                "Configuration template not found. Searched in: " + 
                ", ".join(str(p) for p in possible_paths)
            )
            
        try:
            with open(template_path, 'r') as f:
                content = f.read()
                self.logger.info(f"Loaded configuration template from {template_path}")
                return content
        except Exception as e:
            raise ConfigError(f"Error loading template: {str(e)}")

    def create_config(self, expert_recommendations: Dict[str, Any], watershed_name: str) -> str:
        """Create a new configuration based on template and expert recommendations."""
        try:
            # Start with template content
            config_content = self.template_content
            
            # Create a dictionary of replacements
            replacements = {
                'DOMAIN_NAME': f"'{watershed_name}'",
                'EXPERIMENT_ID': f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            }
            
            # Add expert recommendations to replacements
            for field in self.modifiable_fields:
                if field in expert_recommendations:
                    value = expert_recommendations[field]
                    # Handle string values
                    if isinstance(value, str):
                        replacements[field] = f"'{value}'"
                    else:
                        replacements[field] = str(value)
            
            # Process template line by line
            lines = config_content.split('\n')
            processed_lines = []
            
            for line in lines:
                if ':' in line and not line.strip().startswith('#'):
                    key = line.split(':')[0].strip()
                    if key in replacements:
                        # Preserve indentation and comments
                        indentation = line[:len(line) - len(line.lstrip())]
                        comment = line.split('#')[1].strip() if '#' in line else ''
                        new_line = f"{indentation}{key}: {replacements[key]}"
                        if comment:
                            new_line += f"  # {comment}"
                        processed_lines.append(new_line)
                    else:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
            
            config_content = '\n'.join(processed_lines)
            
            # Validate the configuration
            self._validate_config_content(config_content)
            
            return config_content
            
        except Exception as e:
            self.logger.error(f"Error creating configuration: {str(e)}")
            raise ConfigError(f"Failed to create configuration: {str(e)}")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration against requirements."""
        # Check all required fields from template
        missing_fields = []
        for field in self.template_dict.keys():
            if field not in config:
                missing_fields.append(field)
        
        if missing_fields:
            raise ConfigValidationError(
                "Missing required configuration fields",
                details={"missing_fields": missing_fields}
            )
        
        # Validate modifiable fields have valid values
        valid_options = {
            'HYDROLOGICAL_MODEL': ["SUMMA", "FLASH", "GR", "FUSE", "HYPE", "MESH"],
            'DOMAIN_DEFINITION_METHOD': ["subset", "delineate", "lumped"],
            'ROUTING_MODEL': ["mizuroute"],
            'FORCING_DATASET': ["RDRS", "ERA5"],
            'DOMAIN_DISCRETIZATION': ["elevation", "soilclass", "landclass", "radiation", "GRUs", "combined"]
        }
        
        invalid_values = {}
        for field, valid_values in valid_options.items():
            if field in config and config[field] not in valid_values:
                invalid_values[field] = {
                    'provided': config[field],
                    'valid_options': valid_values
                }
        
        if invalid_values:
            raise ConfigValidationError(
                "Invalid values in configuration",
                details={"invalid_values": invalid_values}
            )
        
        return True

    def _validate_config_content(self, config_content: str) -> None:
        """Validate configuration content."""
        try:
            config = yaml.safe_load(config_content)
            self.validate_config(config)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML format: {str(e)}")

    def save_config(self, config_content: str, output_path: Optional[Path] = None) -> Path:
        """Save configuration to file with backup."""
        try:
            # Parse config to get domain name for default path
            config_dict = yaml.safe_load(config_content)
            domain_name = config_dict.get('DOMAIN_NAME', 'unnamed')
            
            if output_path and output_path.exists():
                self._backup_config(output_path)
            
            if not output_path:
                output_path = Path(f"0_config_files/config_{domain_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
            
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(config_content)
            
            self.logger.info(f"Configuration saved to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            raise ConfigError(f"Failed to save configuration: {str(e)}")

    
    def _backup_config(self, config_path: Path) -> None:
        """Create backup of existing configuration file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.config_backup_dir / f"{config_path.stem}_{timestamp}{config_path.suffix}"
        
        shutil.copy2(config_path, backup_path)
        self.logger.info(f"Created configuration backup: {backup_path}")
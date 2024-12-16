#!/usr/bin/env python3

import os
import sys
from pathlib import Path
import argparse
import yaml # type: ignore
from typing import Optional, Dict, Any
import subprocess

from utils.expert_system import ExpertPanel # type: ignore
from utils.config_handler import ConfigHandler # type: ignore
from utils.purpose_parser import PurposeParser # type: ignore
from utils.logging_setup import setup_logging # type: ignore
from utils.exceptions import INDRAError # type: ignore

class INDRA:
    """
    Intelligent Network for Dynamic River Analysis (INDRA)
    
    A hydrological modeling expert system that assists in model configuration,
    analysis, and evaluation through AI-powered expert consultation.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise INDRAError("No API key provided. Set ANTHROPIC_API_KEY environment variable or provide key in initialization.")
        
        # Setup logging
        self.logger = setup_logging('INDRA')
        self.logger.info("Initializing INDRA system")
        
        # Initialize components
        self.config_handler = ConfigHandler(self.logger)
        self.purpose_parser = PurposeParser(self.api_key, self.logger)
        self.expert_panel = None
        
        # Initialize CONFLUENCE paths
        self.config_path = None
        self.confluence = None

    def run_confluence(self, config_path: Path) -> Dict[str, Any]:
        """
        Execute CONFLUENCE model with given configuration.
        """
        try:
            self.logger.info(f"Initializing CONFLUENCE with config: {config_path}")
            
            # Run CONFLUENCE as a subprocess
            cmd = [
                sys.executable,  # Current Python interpreter
                str(Path(__file__).parent.parent / 'CONFLUENCE' / 'CONFLUENCE.py'),
                '--config',
                str(config_path)
            ]
            
            self.logger.info(f"Running command: {' '.join(cmd)}")
            
            # Run the process
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.logger.info("CONFLUENCE execution completed successfully")
            self.logger.debug(f"CONFLUENCE output:\n{result.stdout}")
            
            if result.stderr:
                self.logger.warning(f"CONFLUENCE stderr:\n{result.stderr}")
            
            # Get results
            results = self.get_confluence_results()
            return results
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"CONFLUENCE execution failed with code {e.returncode}")
            self.logger.error(f"stdout:\n{e.stdout}")
            self.logger.error(f"stderr:\n{e.stderr}")
            raise INDRAError(f"CONFLUENCE execution failed with code {e.returncode}")
        except Exception as e:
            self.logger.error(f"Error running CONFLUENCE: {str(e)}")
            raise INDRAError(f"CONFLUENCE execution failed: {str(e)}")

    def _extract_watershed_name(self, purpose_text: str) -> str:
        """
        Extract watershed name from purpose text.
        
        Args:
            purpose_text: Natural language description of modeling purpose
            
        Returns:
            Extracted watershed name
        """
        try:
            # Create a prompt to extract the watershed name
            prompt = f"""
            Extract only the watershed or river name from this text: {purpose_text}
            Format your response as a single word or phrase, with no punctuation or extra text.
            For example, if input is "Model the flow in Mississippi River", respond with: Mississippi
            If multiple watersheds are mentioned, pick the main one.
            """
            
            response = self.purpose_parser.api.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=50,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            watershed_name = response.content[0].text.strip()
            self.logger.debug(f"Extracted watershed name: {watershed_name}")
            
            # Clean the watershed name for use in filenames
            cleaned_name = ''.join(c for c in watershed_name if c.isalnum() or c in ['-', '_']).strip('-_')
            if not cleaned_name:
                cleaned_name = "unnamed_watershed"
            
            return cleaned_name
            
        except Exception as e:
            self.logger.error(f"Error extracting watershed name: {str(e)}")
            return "unnamed_watershed"

    def get_confluence_results(self) -> Dict[str, Any]:
        """Get results from CONFLUENCE execution."""
        if not self.confluence:
            raise INDRAError("CONFLUENCE not initialized")
            
        try:
            # Get config to find output locations
            config = self.confluence.config
            
            # Construct results dictionary
            results = {
                'status': 'completed',
                'output_dir': str(Path(config['CONFLUENCE_DATA_DIR']) / 
                                f"domain_{config['DOMAIN_NAME']}/simulations/{config['EXPERIMENT_ID']}"),
                'model': config['HYDROLOGICAL_MODEL']
            }
            
            # Add model-specific results
            if config['HYDROLOGICAL_MODEL'] == 'SUMMA':
                results.update(self._get_summa_results(config))
            elif config['HYDROLOGICAL_MODEL'] == 'MESH':
                results.update(self._get_mesh_results(config))
            # Add other models as needed
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting CONFLUENCE results: {str(e)}")
            raise INDRAError(f"Failed to get results: {str(e)}")

    def run(self, model_purpose: str, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """Main entry point for INDRA workflow."""
        try:
            self.logger.info("Starting INDRA workflow")
            self.logger.info(f"Model purpose: {model_purpose}")
            
            # Parse modeling purpose
            purpose_dict = self.purpose_parser.parse(model_purpose)
            self.logger.info("Parsed modeling requirements")
            
            # Extract watershed name
            watershed_name = self._extract_watershed_name(model_purpose)
            self.logger.info(f"Working with watershed: {watershed_name}")
            
            if config_path:
                # Analyze existing configuration
                self.logger.info(f"Analyzing existing configuration: {config_path}")
                config = self.config_handler.load_config(config_path)
                self.expert_panel = ExpertPanel(
                    api_key=self.api_key,
                    model_purpose=purpose_dict,
                    logger=self.logger
                )
                analysis_results = self.expert_panel.analyze_config(config)
                self.config_path = config_path
            else:
                # Generate new configuration
                self.logger.info("Generating new configuration")
                self.expert_panel = ExpertPanel(
                    api_key=self.api_key,
                    model_purpose=purpose_dict,
                    logger=self.logger
                )
                expert_recommendations = self.expert_panel.generate_config(purpose_dict)
                
                # Create and save configuration
                config_content = self.config_handler.create_config(
                    expert_recommendations=expert_recommendations,
                    watershed_name=watershed_name
                )
                self.config_path = self.config_handler.save_config(config_content)
                
                # Run CONFLUENCE
                self.logger.info("Running CONFLUENCE with generated configuration")
                confluence_results = self.run_confluence(self.config_path)
                
                analysis_results = {
                    "config": yaml.safe_load(config_content),
                    "confluence_results": confluence_results
                }
            
            self.logger.info("INDRA workflow completed successfully")
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Error in INDRA workflow: {str(e)}")
            raise

    def _get_summa_results(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get SUMMA-specific results."""
        results = {}
        try:
            output_dir = Path(config['CONFLUENCE_DATA_DIR']) / f"domain_{config['DOMAIN_NAME']}"
            
            # Add paths to specific output files
            results['output_files'] = {
                'streamflow': str(output_dir / 'simulations' / config['EXPERIMENT_ID'] / 
                                'mizuRoute' / f"{config['EXPERIMENT_ID']}.nc"),
                'state_files': str(output_dir / 'simulations' / config['EXPERIMENT_ID'] / 
                                 'SUMMA' / 'stateFiles')
            }
            
        except Exception as e:
            self.logger.warning(f"Error getting SUMMA results: {str(e)}")
            
        return results

    def _get_mesh_results(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get MESH-specific results."""
        results = {}
        try:
            output_dir = Path(config['CONFLUENCE_DATA_DIR']) / f"domain_{config['DOMAIN_NAME']}"
            
            # Add paths to specific output files
            results['output_files'] = {
                'streamflow': str(output_dir / 'simulations' / config['EXPERIMENT_ID'] / 
                                'MESH' / f"{config['EXPERIMENT_ID']}.txt"),
                'diagnostics': str(output_dir / 'simulations' / config['EXPERIMENT_ID'] / 
                                 'MESH' / 'diagnostics')
            }
            
        except Exception as e:
            self.logger.warning(f"Error getting MESH results: {str(e)}")
            
        return results
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration against CONFLUENCE requirements.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            bool: True if configuration is valid
        """
        return self.config_handler.validate_config(config)

def main():
    """Command line entry point for INDRA."""
    parser = argparse.ArgumentParser(
        description="INDRA - Intelligent Network for Dynamic River Analysis"
    )
    parser.add_argument(
        "--purpose",
        type=str,
        required=True,
        help="Natural language description of modeling purpose"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to existing CONFLUENCE configuration file (optional)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Anthropic API key (optional, can use ANTHROPIC_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    try:
        indra = INDRA(api_key=args.api_key)
        results = indra.run(
            model_purpose=args.purpose,
            config_path=args.config
        )
        print("INDRA workflow completed successfully")
        print("\nResults:")
        print(yaml.dump(results, default_flow_style=False))
        
    except INDRAError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
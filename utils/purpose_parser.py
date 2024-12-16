from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass, asdict
import json
import anthropic # type: ignore
from pathlib import Path
from datetime import datetime

from utils.exceptions import PurposeParserError # type: ignore

@dataclass
class ModelingRequirements:
    """Structured representation of modeling requirements"""
    temporal_scale: Dict[str, Any]  # e.g., {'type': 'continuous', 'resolution': 'hourly'}
    spatial_scale: Dict[str, Any]   # e.g., {'type': 'distributed', 'resolution': '1km'}
    key_processes: List[str]        # e.g., ['snow accumulation', 'snowmelt', 'infiltration']
    required_outputs: List[str]     # e.g., ['streamflow', 'soil moisture']
    analysis_requirements: List[str] # e.g., ['uncertainty analysis', 'parameter sensitivity']
    constraints: Dict[str, Any]     # e.g., {'computational': 'high-performance', 'data': 'limited'}
    specific_concerns: List[str]    # User's specific concerns or focus areas

    def to_dict(self) -> Dict[str, Any]:
        """Convert requirements to dictionary format."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelingRequirements':
        """Create ModelingRequirements instance from dictionary."""
        return cls(**data)

class PurposeParser:
    """Parses natural language descriptions of modeling purposes into structured requirements."""
    
    def __init__(self, api_key: str, logger: logging.Logger):
        self.api = anthropic.Anthropic(api_key=api_key)
        self.logger = logger
        self.requirements_template = self._load_requirements_template()
        self.purpose_dir = Path("parsed_purposes")
        self.purpose_dir.mkdir(exist_ok=True)
    
    def parse(self, purpose_text: str) -> Dict[str, Any]:
        """
        Parse natural language purpose into structured requirements.
        
        Args:
            purpose_text: Natural language description of modeling purpose
            
        Returns:
            Dictionary containing structured requirements
        """
        self.logger.info("Parsing modeling purpose")
        self.logger.debug(f"Raw purpose text: {purpose_text}")
        
        # Extract and enhance requirements
        basic_requirements = self._extract_basic_requirements(purpose_text)
        detailed_requirements = self._enhance_requirements(purpose_text, basic_requirements)
        validated_requirements = self._validate_requirements(detailed_requirements)
        
        # Create ModelingRequirements instance
        requirements = ModelingRequirements(**validated_requirements)
        
        # Save parsed purpose
        self._save_parsed_purpose(purpose_text, requirements.to_dict())
        
        # Return as dictionary for JSON serialization
        return requirements.to_dict()
    
    def _get_ai_response(self, prompt: str) -> Dict[str, Any]:
        """
        Get and parse response from AI service.
        
        Args:
            prompt: Prompt to send to AI service
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            PurposeParserError: If response cannot be parsed or is invalid
        """
        try:
            response = self.api.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0,
                system=(
                    "You are an expert in hydrological modeling requirements analysis. "
                    "Extract and structure modeling requirements precisely and comprehensively. "
                    "Always respond with valid JSON."
                ),
                messages=[{
                    "role": "user",
                    "content": prompt + "\n\nEnsure your response is valid JSON."
                }]
            )
            
            # Get the response text
            response_text = response.content[0].text
            
            # Try to extract JSON if it's embedded in other text
            try:
                # First try direct JSON parsing
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text
                self.logger.debug("Direct JSON parsing failed, attempting to extract JSON from response")
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    return json.loads(json_match.group(0))
                else:
                    raise PurposeParserError(
                        "Could not extract valid JSON from AI response",
                        details={"response": response_text}
                    )
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            self.logger.debug(f"Raw response: {response_text}")
            raise PurposeParserError(
                "Failed to parse AI response as JSON",
                details={"error": str(e), "response": response_text}
            )
        except Exception as e:
            self.logger.error(f"Error getting AI response: {str(e)}")
            raise PurposeParserError(
                "Error getting AI response",
                details={"error": str(e)}
            )

    def _extract_basic_requirements(self, purpose_text: str) -> Dict[str, Any]:
        """Extract basic requirements from purpose text."""
        prompt = f"""
        Analyze the following modeling purpose and extract key requirements:
        
        {purpose_text}
        
        Extract and categorize the following aspects:
        1. Temporal scale and resolution requirements
        2. Spatial scale and resolution needs
        3. Key hydrological processes that need to be modeled
        4. Required model outputs and variables
        5. Analysis requirements (e.g., uncertainty, sensitivity)
        6. Any constraints or limitations
        7. Specific concerns or focus areas
        
        Respond with ONLY a JSON object in the following structure:
        {{
            "temporal_scale": {{
                "type": "continuous/event-based/etc",
                "resolution": "temporal resolution"
            }},
            "spatial_scale": {{
                "type": "distributed/lumped/semi-distributed",
                "resolution": "spatial resolution"
            }},
            "key_processes": ["process1", "process2", ...],
            "required_outputs": ["output1", "output2", ...],
            "analysis_requirements": ["requirement1", "requirement2", ...],
            "constraints": {{
                "computational": "constraints description",
                "data": "data availability description"
            }},
            "specific_concerns": ["concern1", "concern2", ...]
        }}
        
        Do not include any other text, only the JSON object.
        """
        
        return self._get_ai_response(prompt)

    def _enhance_requirements(self, purpose_text: str, basic_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance basic requirements with more specific details."""
        prompt = f"""
        Given these basic requirements:
        {json.dumps(basic_requirements, indent=2)}
        
        And this original purpose description:
        {purpose_text}
        
        Enhance the requirements by:
        1. Identifying any implicit needs not directly stated
        2. Suggesting additional relevant processes to consider
        3. Identifying potential challenges or special considerations
        4. Recommending additional outputs that might be valuable
        
        Respond with ONLY a JSON object using the exact same structure as the input:
        {{
            "temporal_scale": {{
                "type": "enhanced type",
                "resolution": "enhanced resolution"
            }},
            "spatial_scale": {{
                "type": "enhanced type",
                "resolution": "enhanced resolution"
            }},
            "key_processes": ["enhanced process1", "enhanced process2", ...],
            "required_outputs": ["enhanced output1", "enhanced output2", ...],
            "analysis_requirements": ["enhanced requirement1", "enhanced requirement2", ...],
            "constraints": {{
                "computational": "enhanced constraints",
                "data": "enhanced data availability"
            }},
            "specific_concerns": ["enhanced concern1", "enhanced concern2", ...]
        }}
        
        Do not include any other text, only the JSON object.
        """
        
        return self._get_ai_response(prompt)
    
    def _validate_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean up requirements.
        
        Ensures all required fields are present and properly formatted.
        """
        required_fields = {
            'temporal_scale': {'type': str, 'resolution': str},
            'spatial_scale': {'type': str, 'resolution': str},
            'key_processes': list,
            'required_outputs': list,
            'analysis_requirements': list,
            'constraints': dict,
            'specific_concerns': list
        }
        
        validated = {}
        
        for field, field_type in required_fields.items():
            if field not in requirements:
                self.logger.warning(f"Missing required field: {field}")
                if field_type == dict:
                    validated[field] = {}
                elif field_type == list:
                    validated[field] = []
                continue
                
            value = requirements[field]
            
            if field in ['temporal_scale', 'spatial_scale']:
                validated[field] = {
                    'type': str(value.get('type', 'unknown')),
                    'resolution': str(value.get('resolution', 'unknown'))
                }
            elif isinstance(value, field_type):
                validated[field] = value
            else:
                self.logger.warning(f"Invalid type for {field}: expected {field_type}, got {type(value)}")
                if field_type == dict:
                    validated[field] = {}
                elif field_type == list:
                    validated[field] = []
        
        return validated
    
    
    def _load_requirements_template(self) -> Dict[str, Any]:
        """Load template for requirements structure."""
        return {
            "temporal_scale": {
                "type": "",
                "resolution": ""
            },
            "spatial_scale": {
                "type": "",
                "resolution": ""
            },
            "key_processes": [],
            "required_outputs": [],
            "analysis_requirements": [],
            "constraints": {
                "computational": "",
                "data": ""
            },
            "specific_concerns": []
        }
    
    def _save_parsed_purpose(self, raw_text: str, requirements: Dict[str, Any]) -> None:
        """Save parsed purpose and requirements for reference."""
        save_data = {
            "raw_purpose": raw_text,
            "parsed_requirements": requirements,
            "timestamp": datetime.now().isoformat()
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = self.purpose_dir / f"purpose_analysis_{timestamp}.json"
        
        with open(save_path, 'w') as f:
            json.dump(save_data, f, indent=2)
            
        self.logger.info(f"Saved parsed purpose to {save_path}")
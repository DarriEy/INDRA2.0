from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import json
from datetime import datetime
from dataclasses import dataclass, asdict
import anthropic # type: ignore

from utils.exceptions import PurposeParserError, ExpertAnalysisError, ConfigValidationError # type: ignore

@dataclass
class Analysis:
    """Dataclass for storing expert analyses"""
    timestamp: str
    expert_type: str
    context: Dict[str, Any]
    findings: Dict[str, Any]
    recommendations: Dict[str, Any]
    consultation_refs: List[str]  # References to related consultations

@dataclass
class Consultation:
    """Dataclass for storing expert consultations"""
    timestamp: str
    requesting_expert: str
    consulted_expert: str
    question: str
    response: str
    context: Dict[str, Any]
    
class Expert:
    """Base expert class for INDRA expert system"""
    
    def __init__(self, expertise: str, api: anthropic.Anthropic, logger: logging.Logger):
        self.expertise = expertise
        self.api = api
        self.logger = logger
        self.context: Dict[str, Any] = {}
        self.analyses: List[Analysis] = []
        self.consultation_requests: List[Dict[str, Any]] = []
        
    def analyze(self, topic: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform expert analysis on a given topic.
        
        Args:
            topic: Subject of analysis
            context: Current context for analysis
            
        Returns:
            Dictionary containing analysis results
        """
        self.context.update(context)
        
        try:
            prompt = self._generate_analysis_prompt(topic)
            response = self._get_ai_response(prompt)
            
            # Create structured analysis output
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "expert_type": self.expertise,
                "context": context,
                "findings": response.get('findings', {}),
                "recommendations": response.get('recommendations', {}),
                "consultation_refs": []
            }
            
            self.analyses.append(analysis)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in expert analysis: {str(e)}")
            raise ExpertAnalysisError(f"Analysis failed: {str(e)}")
    
    def request_consultation(self, question: str, required_expertise: str) -> None:
        """
        Request consultation from another expert.
        
        Args:
            question: Question to ask
            required_expertise: Type of expert needed for consultation
        """
        self.consultation_requests.append({
            'question': question,
            'required_expertise': required_expertise,
            'timestamp': datetime.now().isoformat()
        })
        
    def provide_consultation(self, question: str, context: Dict[str, Any]) -> str:
        """
        Provide consultation to another expert.
        
        Args:
            question: Question being asked
            context: Context for the consultation
            
        Returns:
            Expert's response to the question
        """
        prompt = self._generate_consultation_prompt(question, context)
        response = self._get_ai_response(prompt)
        return response.get('consultation', '')
    
    def _generate_analysis_prompt(self, topic: str) -> str:
        """Generate prompt for analysis."""
        if topic == "Configuration Generation":
            return f"""
            As an expert in {self.expertise}, generate CONFLUENCE configuration recommendations.
            
            Context:
            {json.dumps(self.context, indent=2)}
            
            You must choose from these specific options:
            1. HYDROLOGICAL_MODEL: Only one of ["SUMMA", "FLASH", "GR", "FUSE", "HYPE", "MESH"]
            2. DOMAIN_DEFINITION_METHOD: Only one of ["subset", "delineate", "lumped"]
            3. ROUTING_MODEL: Only "mizuroute"
            4. FORCING_DATASET: Only one of ["RDRS", "ERA5"]
            5. DOMAIN_DISCRETIZATION: Only one of ["elevation", "soilclass", "landclass", "radiation", "GRUs", "combined"]
            
            If DOMAIN_DISCRETIZATION is "elevation", also specify:
            - ELEVATION_BAND_SIZE (in meters)
            - MIN_HRU_SIZE (in km2)
            
            Provide your response in the following JSON format only:
            {{
                "findings": {{
                    "key_points": ["point1", "point2"],
                    "concerns": ["concern1", "concern2"],
                    "opportunities": ["opportunity1", "opportunity2"]
                }},
                "recommendations": {{
                    "config_settings": {{
                        "HYDROLOGICAL_MODEL": "choose one valid option",
                        "DOMAIN_DEFINITION_METHOD": "choose one valid option",
                        "ROUTING_MODEL": "mizuroute",
                        "FORCING_DATASET": "choose one valid option",
                        "DOMAIN_DISCRETIZATION": "choose one valid option",
                        "ELEVATION_BAND_SIZE": integer value if applicable,
                        "MIN_HRU_SIZE": integer value if applicable
                    }},
                    "immediate_actions": ["action1", "action2"],
                    "long_term_considerations": ["consideration1", "consideration2"]
                }}
            }}
            """
        else:
            return f"""
            As an expert in {self.expertise}, analyze the following topic:
            {topic}
            
            Context:
            {json.dumps(self.context, indent=2)}
            
            Provide your response in the following JSON format only:
            {{
                "findings": {{
                    "key_points": ["point1", "point2"],
                    "concerns": ["concern1", "concern2"],
                    "opportunities": ["opportunity1", "opportunity2"]
                }},
                "recommendations": {{
                    "immediate_actions": ["action1", "action2"],
                    "long_term_considerations": ["consideration1", "consideration2"],
                    "additional_data_needed": ["data1", "data2"]
                }}
            }}
            """
        
    def _generate_consultation_prompt(self, question: str, context: Dict[str, Any]) -> str:
        """Generate prompt for consultation."""
        return f"""
        As an expert in {self.expertise}, provide consultation on:
        {question}
        
        Context:
        {json.dumps(context, indent=2)}
        
        Provide your response in the following format:
        {{
            "consultation": "Your detailed response here"
        }}
        """
    
    def _get_ai_response(self, prompt: str) -> Dict[str, Any]:
        """Get and parse response from AI service."""
        try:
            response = self.api.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0,
                system=(
                    f"You are a world-class expert in {self.expertise}. "
                    "Provide precise, well-reasoned responses based on established science and best practices. "
                    "Respond with valid JSON only, no other text."
                ),
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Get and log the raw response
            response_text = response.content[0].text
            self.logger.debug(f"Raw AI response for {self.expertise}:\n{response_text}")
            
            # Clean the response text
            cleaned_response = response_text.strip()
            
            try:
                return json.loads(cleaned_response)
            except json.JSONDecodeError:
                # Try to extract JSON
                import re
                json_pattern = r'(\{[\s\S]*\})'
                matches = re.search(json_pattern, cleaned_response)
                
                if matches:
                    json_str = matches.group(1)
                    return json.loads(json_str)
                    
                raise ExpertAnalysisError(
                    f"Could not parse AI response as JSON for {self.expertise}",
                    details={"response": cleaned_response}
                )
                
        except Exception as e:
            self.logger.error(f"Error getting AI response for {self.expertise}: {str(e)}")
            raise ExpertAnalysisError(f"Failed to get AI response: {str(e)}")

class ExpertPanel:
    """
    Manages a panel of experts and coordinates their interactions.
    """
    
    def __init__(self, api_key: str, model_purpose: Dict[str, Any], logger: logging.Logger):
        """
        Initialize expert panel.
        
        Args:
            api_key: Anthropic API key
            model_purpose: Parsed modeling purpose and requirements
            logger: Logger instance
        """
        self.api = anthropic.Anthropic(api_key=api_key)
        self.logger = logger
        self.model_purpose = model_purpose
        self.experts: Dict[str, Expert] = {}
        self.consultations: List[Consultation] = []
        self.analysis_path = Path("indra_analyses")
        self.analysis_path.mkdir(exist_ok=True)
        
        # Initialize core experts
        self._initialize_experts()
    
    def _initialize_experts(self) -> None:
        """Initialize expert panel based on model purpose."""
        required_experts = self._determine_required_experts()
        
        for expertise in required_experts:
            self.experts[expertise] = Expert(
                expertise=expertise,
                api=self.api,
                logger=self.logger
            )
            
    def _validate_generated_config(self, config: Dict[str, Any]) -> None:
        """Validate the generated configuration."""
        # Required fields
        required_fields = [
            'HYDROLOGICAL_MODEL',
            'DOMAIN_DEFINITION_METHOD',
            'ROUTING_MODEL',
            'FORCING_DATASET',
            'DOMAIN_DISCRETIZATION'
        ]
        
        # Valid options
        valid_options = {
            'HYDROLOGICAL_MODEL': ["SUMMA", "FLASH", "GR", "FUSE", "HYPE", "MESH"],
            'DOMAIN_DEFINITION_METHOD': ["subset", "delineate", "lumped"],
            'ROUTING_MODEL': ["mizuroute"],
            'FORCING_DATASET': ["RDRS", "ERA5"],
            'DOMAIN_DISCRETIZATION': ["elevation", "soilclass", "landclass", "radiation", "GRUs", "combined"]
        }
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ConfigValidationError(
                "Generated configuration missing required fields",
                details={"missing_fields": missing_fields}
            )
        
        # Validate options
        invalid_values = {}
        for field, valid_values in valid_options.items():
            if field in config and config[field] not in valid_values:
                invalid_values[field] = {
                    'provided': config[field],
                    'valid_options': valid_values
                }
        
        if invalid_values:
            raise ConfigValidationError(
                "Invalid values in generated configuration",
                details={"invalid_values": invalid_values}
            )
        
        # Validate elevation-specific parameters if needed
        if config.get('DOMAIN_DISCRETIZATION') == 'elevation':
            if 'ELEVATION_BAND_SIZE' not in config:
                raise ConfigValidationError(
                    "ELEVATION_BAND_SIZE required when using elevation discretization"
                )
            if 'MIN_HRU_SIZE' not in config:
                raise ConfigValidationError(
                    "MIN_HRU_SIZE required when using elevation discretization"
                )
    
    def _determine_required_experts(self) -> List[str]:
        """Determine required experts based on model purpose."""
        prompt = f"""
        Based on the following modeling purpose and requirements,
        determine which types of experts are needed (maximum 10):
        
        {json.dumps(self.model_purpose, indent=2)}
        
        Response format:
        {{"required_experts": ["expertise1", "expertise2", ...]}}
        """
        
        response = self.api.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        experts_list = json.loads(response.content[0].text).get('required_experts', [])
        return experts_list[:10]  # Ensure maximum of 10 experts
    
    def analyze_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze existing CONFLUENCE configuration.
        
        Args:
            config: Configuration dictionary to analyze
            
        Returns:
            Dictionary containing analysis results
        """
        results = {}
        context = {'config': config, 'purpose': self.model_purpose}
        
        for expertise, expert in self.experts.items():
            analysis = expert.analyze("Configuration Analysis", context)
            results[expertise] = asdict(analysis)
            
            # Handle any consultation requests
            self._process_consultation_requests(expert)
        
        self._save_analysis_results(results)
        return results
    
    def generate_config(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate new CONFLUENCE configuration.
        
        Args:
            requirements: Modeling requirements and constraints
            
        Returns:
            Generated configuration dictionary
        """
        context = {'requirements': requirements, 'purpose': self.model_purpose}
        config = {}
        
        try:
            # Each expert contributes to their relevant config sections
            for expertise, expert in self.experts.items():
                self.logger.debug(f"Getting configuration input from {expertise}")
                
                analysis = expert.analyze("Configuration Generation", context)
                
                # Ensure we get a dictionary of config settings
                if isinstance(analysis, dict) and 'recommendations' in analysis:
                    expert_config = analysis['recommendations'].get('config_settings', {})
                else:
                    self.logger.warning(f"Unexpected analysis format from {expertise}")
                    continue
                    
                if expert_config:
                    self.logger.debug(f"Config contribution from {expertise}: {json.dumps(expert_config, indent=2)}")
                    config.update(expert_config)
                
                # Handle any consultation requests
                self._process_consultation_requests(expert)
            
            if not config:
                raise PurposeParserError("No valid configuration generated by experts")
                
            # Validate the generated configuration
            self._validate_generated_config(config)
            
            return config
            
        except Exception as e:
            self.logger.error(f"Error generating configuration: {str(e)}")
            raise PurposeParserError(f"Failed to generate configuration: {str(e)}")
    
    def _process_consultation_requests(self, requesting_expert: Expert) -> None:
        """Process any pending consultation requests from an expert."""
        for request in requesting_expert.consultation_requests:
            if request['required_expertise'] in self.experts:
                consulted_expert = self.experts[request['required_expertise']]
                
                response = consulted_expert.provide_consultation(
                    request['question'],
                    requesting_expert.context
                )
                
                consultation = Consultation(
                    timestamp=datetime.now().isoformat(),
                    requesting_expert=requesting_expert.expertise,
                    consulted_expert=consulted_expert.expertise,
                    question=request['question'],
                    response=response,
                    context=requesting_expert.context
                )
                
                self.consultations.append(consultation)
                
        # Clear processed requests
        requesting_expert.consultation_requests.clear()
    
    def _save_analysis_results(self, results: Dict[str, Any]) -> None:
        """Save analysis results and consultations to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save analyses
        analysis_file = self.analysis_path / f"analysis_{timestamp}.json"
        with open(analysis_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save consultations
        if self.consultations:
            consultation_file = self.analysis_path / f"consultations_{timestamp}.json"
            with open(consultation_file, 'w') as f:
                json.dump([asdict(c) for c in self.consultations], f, indent=2)
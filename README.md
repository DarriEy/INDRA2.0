# INDRA2.0: Intelligent Network for Dynamic River Analysis

INDRA2.0 is an AI-powered expert system designed to assist in hydrological modeling workflows. It integrates with CONFLUENCE (Community Optimization and Numerical Framework for Large-domain Understanding of Environmental Networks and Computational Exploration) to provide intelligent model configuration, analysis, and optimization.

## Features

- 🤖 AI-powered modeling expertise using Claude-3
- 🌊 Hydrological model configuration assistance
- 📊 Intelligent analysis of model configurations and results
- 🔄 Seamless integration with CONFLUENCE
- 💡 Dynamic expert consultation system
- 📝 Natural language processing of modeling requirements

## Prerequisites

- Python 3.8 or higher
- CONFLUENCE installed and configured
- Anthropic API key for Claude-3

## Installation

1. Clone the repository:
```bash
git clone https://github.com/DarriEy/INDRA2.0.git
cd INDRA2.0
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your Anthropic API key:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

## Usage

1. Basic usage with command line:
```bash
python INDRA.py --purpose "Please model streamflow in the Bow river at Banff"
```

2. Analyze existing configuration:
```bash
python INDRA.py --purpose "Your modeling purpose" --config path/to/config.yaml
```

## Project Structure

```
INDRA2.0/
├── INDRA/
│   ├── __init__.py
│   ├── INDRA.py
│   └── utils/
│       ├── expert_system.py
│       ├── config_handler.py
│       ├── purpose_parser.py
│       ├── logging_setup.py
│       └── exceptions.py
└── tests/
    └── __init__.py
```

## How It Works

INDRA2.0 uses an AI-powered expert system to:

1. Parse natural language modeling requirements
2. Consult with specialized experts (hydrology, data science, etc.)
3. Generate or analyze CONFLUENCE configurations
4. Execute and monitor CONFLUENCE workflows
5. Analyze and report results

## Configuration

INDRA2.0 supports various configuration options:

- Multiple hydrological models (SUMMA, FLASH, GR, FUSE, HYPE, MESH)
- Different domain definition methods
- Various forcing datasets
- Flexible spatial discretization

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT License](LICENSE)

## Citation

If you use INDRA2.0 in your research, please cite:

```bibtex
@software{indra2_2024,
  author = {Eythorsson, Darri},
  title = {INDRA2.0: Intelligent Network for Dynamic River Analysis},
  year = {2024},
  publisher = {GitHub},
  url = {https://github.com/DarriEy/INDRA2.0}
}
```

## Acknowledgments

- CONFLUENCE development team
- Anthropic for Claude-3 API
- Contributors and maintainers

## Support

For support, please:
1. Check the existing issues
2. Create a new issue with detailed description
3. Contact the maintainers

## Future Development

Planned features include:
- Enhanced AI capabilities
- Additional expert types
- Improved result analysis
- Extended model support

## Contact

- Main Developer: Darri Eythorsson
- Repository: [https://github.com/DarriEy/INDRA2.0](https://github.com/DarriEy/INDRA2.0)

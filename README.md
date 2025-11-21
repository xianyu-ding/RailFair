# UK Rail Delay Predictor

A machine learning system for predicting train delays on the UK rail network using National Rail Data Portal APIs.

## 🚂 Project Overview

This project aims to predict train delays by analyzing:
- Historical service performance (HSP API)
- Real-time train movement data (Darwin Push Port)
- Weather conditions
- Network incidents
- Service patterns

## 📊 Data Sources

1. **Historical Service Performance (HSP)**: Past delay data and service metrics
2. **Darwin Push Port**: Real-time train movements and updates
3. **Knowledgebase API**: TOC info, station data, restrictions
4. **Weather APIs**: Meteorological conditions

## 🏗️ Project Structure

```
uk-rail-delay-predictor/
├── data/                  # Data storage
│   ├── raw/              # Raw API responses
│   ├── processed/        # Cleaned datasets
│   └── cache/            # Temporary cache
├── src/                   # Source code
│   ├── data_collection/  # API clients
│   ├── preprocessing/    # Data cleaning
│   ├── models/           # ML models
│   ├── api/              # Prediction API
│   └── utils/            # Helper functions
├── models/               # Trained models and checkpoints
├── notebooks/            # Jupyter notebooks
├── tests/
│   ├── unit/             # Fast pytest suites
│   └── integration/      # End-to-end coverage
├── configs/              # Configuration files
├── scripts/              # Operational + helper scripts (moved from root)
└── docs/
    └── archive/          # Legacy quick starts & phase guides

```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API credentials
nano .env
```

### 3. Test API Connection

```bash
python scripts/test_api_connection.py
```

### 4. Operational Scripts

All orchestration scripts (`run_*`, `check_*`, `monitor_*`, etc.) now live under `scripts/`. Update any personal aliases that referenced the old root-level paths.

## 📝 Development Roadmap

- [x] Day 1: Environment setup and API testing
- [ ] Day 2: Data collection pipeline
- [ ] Day 3: Data preprocessing
- [ ] Day 4: Feature engineering
- [ ] Day 5: Model training
- [ ] Day 6: Model evaluation
- [ ] Day 7: API deployment

## 🔗 API Documentation

- [HSP API](https://wiki.openraildata.com/index.php/HSP)
- [Darwin Push Port](https://wiki.openraildata.com/index.php/Darwin:Push_Port)
- [Knowledgebase](https://wiki.openraildata.com/index.php/KnowledgeBase)

## 📄 License

This project is for educational purposes only.

## 👥 Contributing

Please ensure all API credentials are kept secure and never committed to the repository.

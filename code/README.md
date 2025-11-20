# Mycelium Autonomous Orchestrator

Autonomous server infrastructure orchestration system that manages self-provisioning, Bitcoin-funded VPS deployment, and content distribution.

## Architecture

The orchestrator runs continuously and:
- Monitors GitHub repository for code updates every 30 seconds
- Automatically pulls changes and restarts when updates are detected
- Manages future Bitcoin wallet operations (planned)
- Provisions child VPS instances (planned)
- Coordinates BitTorrent seeding operations (planned)

## Local Development Setup

### Prerequisites
- Python 3.7+
- Git
- VirtualBox and Vagrant (for local testing)

### Initial VM Setup

1. Run the first-time setup script:
```bash
cd scripts
./first_spinup.sh
```

This will:
- Create and provision a Vagrant VM
- Install required system packages
- Clone the mycelium repository
- Install Python dependencies

### Deployment

Deploy the orchestrator to the VM:
```bash
cd scripts
./deploy.sh
```

### Monitoring

View orchestrator logs:
```bash
ssh -p 2222 -i ~/.vagrant.d/insecure_private_key vagrant@localhost 'tail -f /home/vagrant/logs/orchestrator.log'
```

### Testing Auto-Update

1. Make a change to the codebase (e.g., modify a log message in `code/main.py`)
2. Commit and push to GitHub
3. Within 30 seconds, the orchestrator will detect the change
4. The orchestrator will pull updates and restart automatically
5. Verify the change in the logs

## Configuration

Configuration is managed via environment variables with defaults in `code/config.py`:

- `MYCELIUM_REPO_URL`: Git repository URL
- `MYCELIUM_BRANCH`: Branch to track (default: main)
- `MYCELIUM_UPDATE_INTERVAL`: Update check interval in seconds (default: 30)
- `MYCELIUM_LOG_LEVEL`: Logging level (default: INFO)

## Project Structure

```
code/
├── main.py              # Entry point and orchestrator loop
├── config.py            # Configuration management
├── modules/
│   ├── code_sync.py     # Git synchronization
│   ├── wallet.py        # Bitcoin operations (planned)
│   ├── provisioner.py   # VPS provisioning (planned)
│   └── seedbox.py       # BitTorrent operations (planned)
├── utils/
│   └── logger.py        # Logging utilities
└── requirements.txt     # Python dependencies
```

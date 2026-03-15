# Urgap Docker Hub

Automated Docker image builds for Urgap packages using GitHub Actions.

## Overview

This repository builds and publishes Docker images for Urgap packages to GitHub Container Registry (GHCR). Each package contains:
- A specific tool or functionality (e.g., plink, filtertabular)
- The Urgap framework with relevant nodes
- Required dependencies and runtime environment

## Supported Packages

### Plink
Bioinformatics tool for genomic data analysis with PlinkFreq nodes.

- **Base image**: `miguelpmachado/plink_2.0` (multi-stage extraction)
- **Available versions**: 2.00a2.3-01
- **GHCR images**: `ghcr.io/urgap/plink:2.00a2.3-01`, `ghcr.io/urgap/plink:latest`
- **Nodes**: PlinkFreq:latest
- **Special features**: Multi-stage build extracts plink2 binary from vendor image

### Filtertabular
Data filtering and format conversion utilities.

- **Base image**: `python:3.10`
- **Available versions**: 1.0.0
- **GHCR images**: `ghcr.io/urgap/filtertabular:1.0.0`, `ghcr.io/urgap/filtertabular:latest`
- **Nodes**: FilterTabularToCSV, FilterTabularToParquet, FilterTabularToXlsx (versions: 1.0.0, latest)
- **Special features**: Single-stage build with uv package manager

## Local Development

### Building Images Locally

Use the `build-local.sh` script:

```bash
# Syntax
./build-local.sh <package> <wheel-path> [version]

# Examples
./build-local.sh plink /path/to/urgap-3.2.18-py3-none-any.whl
./build-local.sh filtertabular /path/to/urgap-3.2.18-py3-none-any.whl 1.0.0
```

The script:
1. Reads configuration from `package-information.json`
2. Finds the appropriate Dockerfile in the package directory
3. Builds the image with version and latest tags
4. Runs tests inside the container

### Interactive Testing

After building, test interactively:

```bash
# Plink
docker run -it --rm ghcr.io/urgap/plink:latest /bin/bash
plink2 --version
python -c "import urgap; print(urgap.__version__)"
uctl --help

# Filtertabular
docker run -it --rm ghcr.io/urgap/filtertabular:latest /bin/bash
python --version
python -c "import urgap; print(urgap.__version__)"
uv --version
uctl --help
```

## CI/CD Workflow

### Automatic Builds

Pushes to the `main` branch automatically build all packages.

### Manual Builds

Trigger builds via GitHub Actions:
1. Go to Actions → "Build and Push Docker Images"
2. Click "Run workflow"
3. Optionally filter by package name (e.g., "plink" builds only plink)

### Workflow Details

The workflow (`.github/workflows/build-and-push.yaml`):

1. **Parse configuration**: Reads `package-information.json` and generates build matrix
2. **Download wheel**: Fetches Urgap wheel from releases or URL
3. **Build images**: Builds Docker images with appropriate Dockerfiles
4. **Run tests**: Executes package-specific tests inside containers
5. **Push to GHCR**: Tags and pushes images with version and latest tags

### Image Tagging Strategy

Each build produces multiple tags:
- `<package>:<version>` - Specific version (e.g., `plink:2.00a2.3-01`)
- `<package>:<version>-urgap<X.Y.Z>` - Version with Urgap version (e.g., `plink:2.00a2.3-01-urgap3.2.18`)
- `<package>:latest` - Latest version of the package (only for the newest version)

## Configuration

### package-information.json Schema

```json
{
    "urgap": "3.2.18",
    "packages": [
        {
            "name": "package-name",
            "versions": ["1.0.0", "2.0.0"],
            "base_image": "base:image",
            "gh_url": "https://github.com/repo",
            "separate_venv": true
        }
    ]
}
```

**Fields**:
- `urgap`: Urgap framework version (applies to all packages)
- `name`: Package directory name (must match directory)
- `versions`: List of versions to build (last version gets "latest" tag)
- `base_image`: Docker base image (append `:` to auto-version, e.g., `image:` → `image:1.0.0`)
- `gh_url`: Source repository URL (informational)
- `separate_venv`: Whether package uses isolated venv (affects test execution)
- `dockerfile`: Optional custom Dockerfile name (defaults to "Dockerfile")

### Validation

The parser validates:
- Package directories exist
- Dockerfiles exist
- Version lists are non-empty

Validation errors cause the build to fail immediately.

## Adding New Packages

1. **Create package directory**: `mkdir <package-name>`

2. **Create Dockerfile**: Choose pattern based on needs:

   **Single-stage** (pure Python, no binary extraction):
   ```dockerfile
   ARG BASEIMAGE
   FROM ${BASEIMAGE}

   ARG URGAP

   # Create user
   RUN addgroup --system nonroot && \
       adduser --system --ingroup nonroot --home /home/nonroot nonroot

   # Copy wheel
   COPY ${URGAP} /home/nonroot

   # Setup venv
   ENV HOME=/home/nonroot
   ENV VENV_PATH=$HOME/venv
   ENV PATH=$VENV_PATH/bin:$PATH
   USER nonroot

   RUN python -m venv "$VENV_PATH" --system-site-packages
   RUN pip install uv
   RUN uv pip install /home/nonroot/${URGAP}["all"]

   WORKDIR $HOME
   ENTRYPOINT ["uctl", "run", "upi-server", "-n", "NodeName:version"]
   ```

   **Multi-stage** (extract binary from vendor image):
   ```dockerfile
   ARG BASEIMAGE

   FROM ${BASEIMAGE} AS binary-source
   RUN cp $(which binary) /tmp/binary

   FROM python:3.11-slim

   ARG URGAP

   COPY --from=binary-source /tmp/binary /usr/local/bin/binary

   RUN useradd -m -s /bin/bash nonroot
   USER nonroot
   WORKDIR /home/nonroot

   RUN python -m venv /home/nonroot/venv
   COPY --chown=nonroot:nonroot ${URGAP} /tmp/
   RUN /home/nonroot/venv/bin/pip install --upgrade pip && \
       WHEEL=$(ls /tmp/*.whl) && \
       /home/nonroot/venv/bin/pip install "${WHEEL}[all]"

   ENV PATH="/home/nonroot/venv/bin:$PATH"
   ENTRYPOINT ["/home/nonroot/venv/bin/uctl", "run", "upi-server"]
   CMD ["-n", "NodeName:latest"]
   ```

3. **Create tests**: `<package-name>/tests/test_<package-name>.py`
   - Test tool availability
   - Test urgap installation
   - Test node registration
   - Test uctl availability

4. **Update package-information.json**: Add package entry

5. **Test locally**: `./build-local.sh <package> <wheel-path>`

6. **Commit and push**: CI will build and push to GHCR

## Dockerfile Patterns

### Separate Venv (true)
- Creates isolated virtual environment
- Installs urgap with explicit pip path (`/home/nonroot/venv/bin/pip`)
- Tests use venv-scoped commands
- Example: plink

### System Site Packages (false)
- Creates venv with `--system-site-packages`
- Allows access to base image packages
- Tests use system commands (`pip3`, `pytest`)
- Example: filtertabular

## Testing Approach

Each package has a test suite in `<package>/tests/test_<package>.py` that verifies:
1. Core tools are available (e.g., `plink2`, `python`)
2. Urgap is installed correctly
3. Package-specific nodes are registered
4. CLI tools work (`uctl`, `uv`)

Tests run inside containers during CI using pytest.

## Migration from Azure DevOps

This implementation replaces the Azure DevOps pipeline with GitHub Actions:

**Key differences**:
- **Registry**: GHCR instead of ACR
- **Configuration**: Declarative JSON (manual commits) instead of dynamic updates
- **Matrix generation**: Simple Python parser instead of Azure-specific scripts
- **Workflows**: GitHub Actions YAML instead of Azure Pipelines YAML

**Removed components**:
- `helpers/get_urls.py` - Multi-repo checkout (GitHub doesn't need this)
- `helpers/parse_json.py` - Azure-specific JSON updates
- Dynamic JSON updates during CI

**Benefits**:
- Simpler architecture (no dynamic JSON updates)
- Better version control (JSON changes are explicit commits)
- Native GitHub integration (Actions, GHCR, permissions)
- Public container registry (GHCR vs private ACR)

## Troubleshooting

### Build fails with "Package directory not found"
Ensure the package name in `package-information.json` matches the directory name exactly.

### Tests fail with "command not found"
Check `separate_venv` setting and test file paths:
- `true`: Use `/home/nonroot/venv/bin/<command>`
- `false`: Use system commands (`pip3`, `pytest`)

### Image doesn't push to GHCR
Ensure workflow has `packages: write` permission and GITHUB_TOKEN is valid.

## Repository Structure

```
.
├── .github/
│   └── workflows/
│       └── build-and-push.yaml    # CI/CD workflow
├── helpers/
│   └── parse_packages.py          # Matrix generator with validation
├── plink/
│   ├── Dockerfile                 # Multi-stage plink build
│   └── tests/
│       └── test_plink.py          # Plink tests
├── filtertabular/
│   ├── Dockerfile                 # Single-stage Python build
│   └── tests/
│       └── test_filtertabular.py  # Filtertabular tests
├── package-information.json       # Package configuration
├── build-local.sh                 # Local build script
└── README.md                      # This file
```

## License

See individual package repositories for licensing information.

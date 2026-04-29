# Publishing

This project is ready for both PyPI and Homebrew-style distribution.

## PyPI

The recommended PyPI path is Trusted Publishing from GitHub Actions. This avoids storing a long-lived PyPI token in GitHub secrets.

### One-time PyPI setup

1. Create or log into a PyPI account.
2. Open the PyPI trusted publisher settings.
3. Add a pending publisher with:

```text
PyPI project name: cfgsync
Owner: alanzeng423
Repository name: config_management
Workflow name: publish-pypi.yml
Environment name: pypi
```

4. In GitHub, create an environment named `pypi` for this repository.

### Publish

Create a GitHub release:

```bash
gh release create v0.1.0 \
  --title "cfgsync v0.1.0" \
  --notes "Initial cfgsync release."
```

Publishing the release triggers `.github/workflows/publish-pypi.yml`, which builds the wheel and source distribution and uploads both to PyPI.

You can also run the `Publish to PyPI` workflow manually from GitHub Actions after the trusted publisher is configured.

### Token fallback

If you prefer an API token instead of Trusted Publishing:

```bash
python3 -m pip install --upgrade build twine
python3 -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-... python3 -m twine upload dist/*
```

## Homebrew

Homebrew distribution usually needs a tap repository, for example:

```text
github.com/alanzeng423/homebrew-tap
```

After a GitHub release exists, update the formula from:

```text
packaging/homebrew/cfgsync.rb.template
```

The formula needs the release tarball URL and SHA256:

```bash
curl -L https://github.com/alanzeng423/config_management/archive/refs/tags/v0.1.0.tar.gz -o cfgsync-0.1.0.tar.gz
shasum -a 256 cfgsync-0.1.0.tar.gz
```

Users can install from the tap with:

```bash
brew tap alanzeng423/tap
brew install cfgsync
```

For now, PyPI or `pipx` is the cleaner first public release path because the package is pure Python and has optional R2/S3 dependencies.

"""Basic tests for plink container."""

import subprocess


def test_plink2_available():
    """Test that plink2 binary is available and runs."""
    result = subprocess.run(
        ["plink2", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "PLINK" in result.stdout


def test_urgap_installed():
    """Test that urgap package is installed."""
    result = subprocess.run(
        ["/home/nonroot/venv/bin/pip", "show", "urgap"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Name: urgap" in result.stdout


def test_plinkfreq_node_registered():
    """Test that PlinkFreq node is discovered by urgap."""
    result = subprocess.run(
        ["/home/nonroot/venv/bin/python", "-c",
         "import urgap; print('PlinkFreq:latest' in urgap.instances.unode_manager.wrapper_lookup)"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "True" in result.stdout


def test_uctl_available():
    """Test that uctl command is available."""
    result = subprocess.run(
        ["/home/nonroot/venv/bin/uctl", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "uctl" in result.stdout.lower() or "urgap" in result.stdout.lower()

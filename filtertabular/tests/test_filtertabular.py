"""Basic tests for filtertabular container."""

import subprocess


def test_python_available():
    """Test that Python is available and runs."""
    result = subprocess.run(
        ["python", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Python" in result.stdout


def test_urgap_installed():
    """Test that urgap package is installed."""
    result = subprocess.run(
        ["pip", "show", "urgap"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Name: urgap" in result.stdout


def test_filtertabular_nodes_registered():
    """Test that FilterTabular nodes are discovered by urgap."""
    result = subprocess.run(
        ["python", "-c",
         "import urgap; "
         "lookup = urgap.instances.unode_manager.wrapper_lookup; "
         "print(all(node in lookup for node in ["
         "'FilterTabularToCSV:1.0.0', 'FilterTabularToParquet:1.0.0', 'FilterTabularToXlsx:1.0.0', "
         "'FilterTabularToCSV:latest', 'FilterTabularToParquet:latest', 'FilterTabularToXlsx:latest']))"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "True" in result.stdout


def test_uctl_available():
    """Test that uctl command is available."""
    result = subprocess.run(
        ["uctl", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "uctl" in result.stdout.lower()
    assert "urgap" in result.stdout.lower()



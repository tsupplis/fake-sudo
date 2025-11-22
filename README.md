# sudo - Compatibility Wrapper

[![License](https://img.shields.io/badge/License-BSD-blue.svg)](https://opensource.org/licenses/BSD)
[![Language](https://img.shields.io/badge/language-c-blue.svg)](https://en.wikipedia.org/wiki/c_(programming_language))

A POSIX-compliant shell script that provides `sudo`-like functionality by mapping commands to `doas` when available, or falling back to plain shell execution when `doas` is not installed.

## Overview

This script serves as a compatibility layer that:
- **With doas**: Maps `sudo` options to their `doas` equivalents
- **Without doas**: Executes commands directly using the shell (no privilege escalation)

## Features

### Help Output

The `--help` output adapts based on whether doas is available:

#### With doas installed:
```
Mode: Using doas backend (privilege escalation enabled)

Fully supported options:
  -u, -n, -s, -i, -b, -a, -C, -L, -l

Limited support with warnings:
  -v, -k, -K, -E, -g, -H
```

#### Without doas:
```
Mode: Using shell backend (NO privilege escalation)

Working options:
  -s, -i, -b (execute as current user)

Ignored options (warnings shown):
  -u, -n, -g, -a, -C, -L, -l, -v, -k, -K, -E, -H
```

### Supported Options by Scenario

#### Universal Options (work in both scenarios)
- `-h, --help` - Display context-aware help message
- `-V, --version` - Display version information
- `-s, --shell` - Run shell (as target user with doas, as current user without)
- `-i, --login` - Run login shell (as target user with doas, as current user without)
- `-b, --background` - Run command in background
- `--` - End of options delimiter

#### doas Backend Options (require doas installation)
- `-u user, --user=user` - Run command as specified user (default: root)
- `-n, --non-interactive` - Non-interactive mode, fail if password required
- `-a style` - Use specified authentication style
- `-C config` - Check configuration file
- `-L, --clear-persist` - Clear persisted authentication
- `-l, --list` - List doas configuration

#### Limited Support Options (warnings issued)
- `-v, --validate` - Update cached credentials (limited support with doas)
- `-k, --reset-timestamp` - Invalidate cached credentials (limited support with doas)
- `-K, --remove-timestamp` - Remove all cached credentials (limited support with doas)
- `-E, --preserve-env` - Preserve user environment (limited support with doas)
- `-g group, --group=group` - Run with specified group (not supported by doas)
- `-H, --set-home` - Set HOME to target user's home (not implemented)

## Behavior

### When doas is available:
- Commands are executed through `doas` with proper privilege escalation
- Options are translated to their `doas` equivalents where possible
- Warnings are shown for unsupported options

### When doas is NOT available:
- Commands are executed directly using the shell **without privilege escalation**
- User switching options (`-u`) are ignored with a warning message
- The script acts as a pass-through wrapper
- Useful for development/testing environments without privilege requirements

## Installation

1. Copy the `sudo` script to a directory in your PATH:
   ```sh
   cp sudo /usr/local/bin/sudo
   chmod +x /usr/local/bin/sudo
   ```

2. Optionally, ensure this directory appears before the system `sudo`:
   ```sh
   export PATH="/usr/local/bin:$PATH"
   ```

## Usage Examples

### Basic command execution
```sh
# With doas: executes as root via doas
# Without doas: executes as current user
sudo ls /root
```

### Specify a user
```sh
# With doas: executes as user 'www'
# Without doas: warning shown, executes as current user
sudo -u www whoami
```

### Run a shell
```sh
# With doas: spawns root shell via doas
# Without doas: spawns regular shell as current user
sudo -s
```

### Non-interactive mode
```sh
# With doas: fails if password required
# Without doas: warning shown, command executed
sudo -n reboot
```

### Background execution
```sh
# Both modes: runs command in background
sudo -b long-running-command
```

### Check doas configuration
```sh
# Requires doas
sudo -C /etc/doas.conf ls /root
```

## Configuration

### doas Configuration
When using `doas` as the backend, configure `/etc/doas.conf`:

```
# Allow user to run commands as root without password
permit nopass username as root

# Allow user to run specific commands
permit username cmd /usr/bin/reboot

# Keep environment variables
permit keepenv username
```

See `doas.conf(5)` for complete configuration details.

### No Configuration Needed for Shell Fallback
When `doas` is not installed, no configuration is needed. Commands run with the current user's privileges.

## Limitations

### General Limitations
- Not all `sudo` options are supported (this is a minimal compatibility layer)
- Complex `sudo` features like plugin architecture are not available
- Credential caching is handled by `doas` (limited compared to `sudo`)

### Shell Fallback Mode Limitations (when doas is not available)
- **No privilege escalation** - commands run as the current user
- User switching (`-u`) is ignored
- Group switching (`-g`) is ignored
- Authentication is bypassed
- Non-interactive mode (`-n`) has no effect

## Compatibility Matrix

| Option | With doas | Without doas |
|--------|-----------|--------------|
| `-u user` | ✅ Full support | ⚠️ Ignored (warning) |
| `-g group` | ⚠️ Not supported | ⚠️ Ignored (warning) |
| `-s` | ✅ Full support | ✅ Current user shell |
| `-i` | ✅ Full support | ✅ Current user shell |
| `-n` | ✅ Full support | ⚠️ Ignored (warning) |
| `-E` | ⚠️ Limited | ✅ N/A (env preserved) |
| `-b` | ✅ Full support | ✅ Full support |
| `-a style` | ✅ Full support | ❌ Not available |
| `-C config` | ✅ Full support | ❌ Not available |
| `-L` | ✅ Full support | ❌ Not available |
| `-v/-k/-K` | ⚠️ Limited | ⚠️ No effect |
| `-l` | ⚠️ Shows config | ⚠️ Shows warning |

## Security Considerations

### ⚠️ Important Security Notes

1. **Shell Fallback is NOT Secure**: When `doas` is not available, this script provides **no security** - it merely executes commands as the current user. This is intentional for development/testing scenarios.

2. **Install doas for Production**: For any system requiring privilege escalation, install and configure `doas` properly:
   - OpenBSD: Built-in
   - Linux: Available in most package managers (`apt install doas`, `yum install doas`, etc.)
   - macOS: Available via Homebrew (`brew install doas`)

3. **Configuration Validation**: Always validate your `doas.conf` configuration:
   ```sh
   doas -C /etc/doas.conf
   ```

4. **Audit Trail**: The `doas` backend provides logging. The shell fallback does not.

## Testing

Test the script's behavior:

```sh
# Test help
./sudo --help

# Test version
./sudo --version

# Test command execution
./sudo echo "Hello World"

# Test with user specification
./sudo -u nobody id

# Test shell invocation
./sudo -s
```

## References

- [doas(1) - OpenBSD Manual](https://man.openbsd.org/doas)
- [doas.conf(5) - OpenBSD Manual](https://man.openbsd.org/doas.conf)
- [sudo(8) - FreeBSD Manual](https://man.freebsd.org/cgi/man.cgi?sudo(8))

## License

This script is provided as-is for compatibility purposes. Use at your own risk.

## Contributing

Contributions are welcome! Please ensure any changes:
- Maintain POSIX shell compatibility
- Preserve the two-mode behavior (doas vs. shell fallback)
- Include appropriate warnings for unsupported features
- Update documentation accordingly

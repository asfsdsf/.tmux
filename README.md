# tmux configuration

This repository contains a tmux setup and a matching Herdr configuration. Both
use `Ctrl-a` as the prefix key.

## Installer

Run the interactive installer from the repository root and select tmux, Herdr,
or both:

```sh
./install.sh
```

The installer supports macOS and Linux. It asks before installing a missing
tmux or Herdr executable, so either program may be installed manually later.
Skipping a program does not skip its configuration. Existing configuration
files are backed up with an `.old` suffix.

## tmux

For a manual installation:

```sh
brew install tmux
```

Add these lines to `~/.tmux.conf`, replacing `/path/to/tmux` with this
repository's path:

```tmux
source-file "/path/to/tmux/tmux.conf"
source-file "/path/to/tmux/white_black_color"
```

Reload a running tmux server:

```sh
tmux source-file ~/.tmux.conf
```

| Shortcut | Action |
| --- | --- |
| `Ctrl-a c` | Create a window |
| `Ctrl-a /` | Split to the right |
| `Ctrl-a -` | Split below |
| `Ctrl-a h/j/k/l` | Move between panes |
| `Ctrl-a w` | Choose a session, window, or pane |
| `Ctrl-a Tab` | Return to the most recently used window |
| `Ctrl-a Enter` | Enter copy mode |
| `Ctrl-a r` | Reload the configuration |

## Herdr

The Herdr configuration, plugin, installation steps, and shortcuts are in
[herdr/README.md](herdr/README.md).

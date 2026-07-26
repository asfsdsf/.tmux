# tmux and Herdr setup

The configuration directory can be stored anywhere. In the examples below,
replace `/path/to/tmux` with the directory containing this README. Both tmux
and Herdr use `Ctrl-a` as the prefix key.

## Interactive installation

Run the installer and use its checkbox-style menu to install tmux, Herdr, or
both. It prompts for this configuration directory and backs up existing tmux
or Herdr configuration files with an `.old` suffix before replacing them.

```sh
./install.sh
```

## tmux

### Install

```sh
brew install tmux
```

### Set up

Add these lines to `~/.tmux.conf`:

```tmux
source-file "/path/to/tmux/tmux.conf"
source-file "/path/to/tmux/white_black_color"
```

Reload the configuration:

```sh
tmux source-file ~/.tmux.conf
```

### Use

Start tmux:

```sh
tmux
```

Useful shortcuts:

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

### Install

```sh
brew install herdr jq python
```

### Set up

Point Herdr at the configuration in this directory:

```sh
mkdir -p ~/.config/herdr
ln -sfn "/path/to/tmux/herdr.toml" ~/.config/herdr/config.toml
```

Install the local tmux-compatibility plugin:

```sh
herdr plugin link "/path/to/tmux/herdr-tmux-compat" --enabled
herdr server reload-config
```

### Use

Start Herdr:

```sh
herdr
```

Connect to a remote server from the local computer:

```sh
herdr --remote user@server
```

Useful shortcuts:

| Shortcut | Action |
| --- | --- |
| `Ctrl-a c` | Create a tab |
| `Ctrl-a /` | Split to the right |
| `Ctrl-a -` | Split below |
| `Ctrl-a h/j/k/l` | Move between panes |
| `Ctrl-a w` | Choose a workspace, tab, or pane |
| `Ctrl-a Tab` | Return to the most recently used tab |
| `Ctrl-a 1` … `9` | Select a tab by number |
| `Ctrl-a x` | Close a pane |
| `Ctrl-a z` | Zoom a pane |
| `Ctrl-a r` | Reload the configuration |
| `Ctrl-a e` | Edit the configuration |

To copy text:

1. Press `Ctrl-a Enter`.
2. Move with vi keys and press `v` to start selecting.
3. Press `y` to copy.
4. Paste locally with `Cmd-v`.

With `herdr --remote`, copied text is forwarded to the local clipboard through
OSC 52. The local terminal must allow OSC 52 clipboard access.

In the `Ctrl-a w` picker, use `j`/`k` to move, `h`/`l` to
collapse/expand, `Enter` to select, and `q` or `Escape` to cancel.

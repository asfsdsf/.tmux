# Herdr configuration

This directory provides a tmux-style Herdr setup for macOS:

- `config.toml` defines the `Ctrl-a` keymap and interface settings.
- `tmux-compat/` adds the pane picker, most-recent-tab switching, and clean copy
  view.

## Install

From the repository root, run `./install.sh` and select Herdr. For a manual
installation, replace `/path/to/tmux` with the repository path:

```sh
brew install herdr jq python
mkdir -p ~/.config/herdr
ln -sfn "/path/to/tmux/herdr/config.toml" ~/.config/herdr/config.toml
herdr plugin link "/path/to/tmux/herdr/tmux-compat" --enabled
herdr config check
herdr server reload-config
```

Start Herdr with `herdr`, or connect to a remote server with:

```sh
herdr --remote user@server
```

## Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl-a c` | Create a tab |
| `Ctrl-a /` | Split to the right |
| `Ctrl-a -` | Split below |
| `Ctrl-a h/j/k/l` | Move between panes |
| `Ctrl-a w` | Choose a workspace, tab, or pane |
| `Ctrl-a Tab` | Return to the most recently used tab |
| `Ctrl-a 1-9` | Select a tab by number |
| `Ctrl-a x` | Close a pane |
| `Ctrl-a z` | Zoom a pane |
| `Ctrl-a m` | Toggle clean pane copy view |
| `Ctrl-a r` | Reload the configuration |
| `Ctrl-a e` | Edit the configuration |

In the pane picker, use `j`/`k` to move, `h`/`l` to collapse or expand,
`Enter` to select, and `q` or `Escape` to cancel.

## Copy text

For Herdr copy mode, press `Ctrl-a Enter`, select with vi keys and `v`, then
press `y`. Remote sessions forward copied text through OSC 52 when the local
terminal permits clipboard access.

Clean copy view zooms the current pane and temporarily disables borders,
scrollbars, and mouse capture so normal terminal selection works. In Ghostty,
add this binding so `Ctrl-a m` also hides the Herdr sidebar:

```ini
keybind = ctrl+a>m=text:\x01b\x01m
```

Press `Ctrl-a m` again to restore the previous layout and mouse settings.

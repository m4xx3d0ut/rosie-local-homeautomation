# Local ADB Debug Keys

`host-adbkey.pub` is the public half of the local build host's ADB key. It is ignored by Git and must not be committed.

When configured in a local profile overlay, the build copies this key to `/adb_keys` in the ramdisk so a freshly wiped development image can authorize ADB before the setup UI is usable.

Regenerate it on the build host with:

```bash
mkdir -p inputs/adb
adb pubkey ~/.android/adbkey > inputs/adb/host-adbkey.pub
```

Then opt in from an ignored overlay such as `profiles/local/site.yaml`:

```yaml
debug:
  adb_public_key: inputs/adb/host-adbkey.pub
```

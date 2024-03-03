# Borgmatic backups on the Windows system tray

This is a Python program that runs [Borgmatic](https://torsion.org/borgmatic/) backups and shows a Windows system tray
icon with the current backup status. It also allows you to manually run backups, set up scheduled backups, and analyze
the backup logs to find the file paths that take the longest time to back up.

## Setup

1. Clone this repo.
2. Install the required packages with `pip install --user -r requirements.txt`. These **must** be installed to the user
   directory, not a virtual environment, because the main script is run by itself as a scheduled task.
3. Inside the WSL distribution you will use to run Borgmatic, install Borg backup, Borgmatic, and optionally Vorta.
   **Tip:** Use a WSL 1 distribution for maximum backup performance in Windows. See the benchmarks below for more
   details. **Note:** Only WSL 2 supports GUI applications like Vorta. Personally, I use an Ubuntu WSL 2 distro as my
   primary distro, so this is my setup.

   In an Ubuntu WSL 2 distro (for WSL backups and the Vorta GUI):

   ```bash
   sudo apt install python3 pipx
   pipx ensurepath
   # --pre is needed to install Borg v2 for now
   pipx install --pip-args=--pre borgbackup borgmatic vorta
   ```

   In an Ubuntu WSL 1 distro (for Windows backups):

   ```bash
    sudo apt install python3 pipx
    pipx ensurepath
    pipx install --pip-args=--pre borgbackup borgmatic
   ```

4. Edit the `main.pyw` file to set up your backup configurations. Check `configuration.py` for the options.
5. Run `main.pyw` once to set up the configuration directory, then right click on the systray icon and quit.
6. Create your [Borgmatic configuration file](https://torsion.org/borgmatic/docs/reference/configuration/). I use one
   for my WSL environment and one for Windows (see the example configurations in this repo).
7. Move your Borgmatic configuration files to the `%APPDATA%\borgmatic-windows-tray\config` directory. Name them
   according to the backup configuration names, like `borgmatic-windows.yml` and `borgmatic-wsl.yml`.
8. Create post-backup scripts for each configuration in the config directory. The scripts should be named
   `post-backup-<name>.sh`. They will be run every few hours after a backup. I use them to copy my backup repositories
   to other storage locations.
9. Create a scheduled task that runs `main.pyw` at logon by running `create-scheduled-task.ps1` as an administrator.
   This will also create a Start menu entry that starts this task immediately.

## Benchmarks

These are a few benchmarks I did using `borg benchmark crud` to compare WSL 1 and WSL 2 performance. The exact numbers
([check the docs](https://borgbackup.readthedocs.io/en/latest/usage/benchmark.html) for an explanation) will be
different depending on the computer, but I observed a consistent pattern of **WSL 1 being about 3 times faster** for
backups from outside WSL (in `/mnt/c`, etc.). WSL 1 apparently has less overhead when crossing file system boundaries,
although both WSL versions are significantly slower at accessing files outside of WSL than inside. Note that the largest
bottleneck for regularly-scheduled backups is checking for changes in files, which WSL 1 is again sigificiantly faster
at for sources outside WSL.

### CPU benchmark (`borg benchmark cpu`)

<details>
<summary>WSL 1</summary>
<pre><code>
Chunkers =======================================================
buzhash,19,23,21,4095    1GB        0.354s
fixed,1048576            1GB        0.028s
Non-cryptographic checksums / hashes ===========================
xxh64                    1GB        0.071s
crc32 (zlib)             1GB        0.174s
Cryptographic hashes / MACs ====================================
hmac-sha256              1GB        0.401s
blake2b-256              1GB        1.024s
Encryption =====================================================
aes-256-ctr-hmac-sha256  1GB        0.561s
aes-256-ctr-blake2b      1GB        3.140s
aes-256-ocb              1GB        0.167s
chacha20-poly1305        1GB        0.338s
KDFs (slow is GOOD, use argon2!) ===============================
pbkdf2                   5          0.096s
argon2                   5          0.248s
Compression ====================================================
lz4          0.1GB      0.004s
zstd,1       0.1GB      0.012s
zstd,3       0.1GB      0.016s
zstd,5       0.1GB      0.036s
zstd,10      0.1GB      0.106s
zstd,16      0.1GB      7.366s
zstd,22      0.1GB      12.060s
zlib,0       0.1GB      0.032s
zlib,6       0.1GB      1.422s
zlib,9       0.1GB      1.435s
lzma,0       0.1GB      9.548s
lzma,6       0.1GB      22.418s
lzma,9       0.1GB      18.802s
msgpack ========================================================
msgpack      100k Items 0.054s
</code></pre>
</details>

<details>
<summary>WSL 2</summary>
<pre><code>
Chunkers =======================================================
buzhash,19,23,21,4095    1GB        0.394s
fixed,1048576            1GB        0.022s
Non-cryptographic checksums / hashes ===========================
xxh64                    1GB        0.070s
crc32 (zlib)             1GB        0.173s
Cryptographic hashes / MACs ====================================
hmac-sha256              1GB        0.403s
blake2b-256              1GB        1.019s
Encryption =====================================================
aes-256-ctr-hmac-sha256  1GB        0.567s
aes-256-ctr-blake2b      1GB        1.394s
aes-256-ocb              1GB        0.149s
chacha20-poly1305        1GB        0.337s
KDFs (slow is GOOD, use argon2!) ===============================
pbkdf2                   5          0.087s
argon2                   5          0.150s
Compression ====================================================
lz4          0.1GB      0.004s
zstd,1       0.1GB      0.012s
zstd,3       0.1GB      0.016s
zstd,5       0.1GB      0.034s
zstd,10      0.1GB      0.076s
zstd,16      0.1GB      6.460s
zstd,22      0.1GB      9.841s
zlib,0       0.1GB      0.030s
zlib,6       0.1GB      1.431s
zlib,9       0.1GB      1.428s
lzma,0       0.1GB      9.317s
lzma,6       0.1GB      20.280s
lzma,9       0.1GB      16.836s
msgpack ========================================================
msgpack      100k Items 0.053s
</code></pre>
</details>

### Repo and backup files inside WSL

<details>
<summary>WSL 1</summary>
<pre><code>
C-Z-BIG         980.40 MB/s (10 * 100.00 MB all-zero files: 1.02s)
R-Z-BIG         697.59 MB/s (10 * 100.00 MB all-zero files: 1.43s)
U-Z-BIG        1900.47 MB/s (10 * 100.00 MB all-zero files: 0.53s)
D-Z-BIG        3421.98 MB/s (10 * 100.00 MB all-zero files: 0.29s)
C-R-BIG         336.01 MB/s (10 * 100.00 MB random files: 2.98s)
R-R-BIG         642.77 MB/s (10 * 100.00 MB random files: 1.56s)
U-R-BIG        1828.33 MB/s (10 * 100.00 MB random files: 0.55s)
D-R-BIG        3497.90 MB/s (10 * 100.00 MB random files: 0.29s)
C-Z-MEDIUM      794.36 MB/s (1000 * 1.00 MB all-zero files: 1.26s)
R-Z-MEDIUM      893.18 MB/s (1000 * 1.00 MB all-zero files: 1.12s)
U-Z-MEDIUM     1166.95 MB/s (1000 * 1.00 MB all-zero files: 0.86s)
D-Z-MEDIUM     3399.36 MB/s (1000 * 1.00 MB all-zero files: 0.29s)
C-R-MEDIUM      382.39 MB/s (1000 * 1.00 MB random files: 2.62s)
R-R-MEDIUM      832.99 MB/s (1000 * 1.00 MB random files: 1.20s)
U-R-MEDIUM     1184.61 MB/s (1000 * 1.00 MB random files: 0.84s)
D-R-MEDIUM     3438.14 MB/s (1000 * 1.00 MB random files: 0.29s)
C-Z-SMALL        16.29 MB/s (10000 * 10.00 kB all-zero files: 6.14s)
R-Z-SMALL        92.21 MB/s (10000 * 10.00 kB all-zero files: 1.08s)
U-Z-SMALL        17.34 MB/s (10000 * 10.00 kB all-zero files: 5.77s)
D-Z-SMALL       281.93 MB/s (10000 * 10.00 kB all-zero files: 0.35s)
C-R-SMALL        14.36 MB/s (10000 * 10.00 kB random files: 6.97s)
R-R-SMALL        96.45 MB/s (10000 * 10.00 kB random files: 1.04s)
U-R-SMALL        16.98 MB/s (10000 * 10.00 kB random files: 5.89s)
D-R-SMALL       275.53 MB/s (10000 * 10.00 kB random files: 0.36s)
</code></pre>
</details>

<details>
<summary>WSL 2</summary>
<pre><code>
C-Z-BIG        1156.42 MB/s (10 * 100.00 MB all-zero files: 0.86s)
R-Z-BIG        1047.53 MB/s (10 * 100.00 MB all-zero files: 0.95s)
U-Z-BIG        5444.89 MB/s (10 * 100.00 MB all-zero files: 0.18s)
D-Z-BIG        9718.19 MB/s (10 * 100.00 MB all-zero files: 0.10s)
C-R-BIG         341.46 MB/s (10 * 100.00 MB random files: 2.93s)
R-R-BIG         744.48 MB/s (10 * 100.00 MB random files: 1.34s)
U-R-BIG        4093.58 MB/s (10 * 100.00 MB random files: 0.24s)
D-R-BIG        9385.86 MB/s (10 * 100.00 MB random files: 0.11s)
C-Z-MEDIUM     1290.66 MB/s (1000 * 1.00 MB all-zero files: 0.77s)
R-Z-MEDIUM     1085.96 MB/s (1000 * 1.00 MB all-zero files: 0.92s)
U-Z-MEDIUM     5884.33 MB/s (1000 * 1.00 MB all-zero files: 0.17s)
D-Z-MEDIUM     8896.08 MB/s (1000 * 1.00 MB all-zero files: 0.11s)
C-R-MEDIUM      361.37 MB/s (1000 * 1.00 MB random files: 2.77s)
R-R-MEDIUM      638.88 MB/s (1000 * 1.00 MB random files: 1.57s)
U-R-MEDIUM     5748.08 MB/s (1000 * 1.00 MB random files: 0.17s)
D-R-MEDIUM     8327.94 MB/s (1000 * 1.00 MB random files: 0.12s)
C-Z-SMALL        44.15 MB/s (10000 * 10.00 kB all-zero files: 2.26s)
R-Z-SMALL       145.19 MB/s (10000 * 10.00 kB all-zero files: 0.69s)
U-Z-SMALL       141.63 MB/s (10000 * 10.00 kB all-zero files: 0.71s)
D-Z-SMALL       511.23 MB/s (10000 * 10.00 kB all-zero files: 0.20s)
C-R-SMALL        30.19 MB/s (10000 * 10.00 kB random files: 3.31s)
R-R-SMALL       133.01 MB/s (10000 * 10.00 kB random files: 0.75s)
U-R-SMALL       139.02 MB/s (10000 * 10.00 kB random files: 0.72s)
D-R-SMALL       404.42 MB/s (10000 * 10.00 kB random files: 0.25s)
</code></pre>
</details>

### Repo inside WSL, backup files outside WSL

<details>
<summary>WSL 1</summary>
<pre><code>
C-Z-BIG         987.25 MB/s (10 * 100.00 MB all-zero files: 1.01s)
R-Z-BIG         689.18 MB/s (10 * 100.00 MB all-zero files: 1.45s)
U-Z-BIG        1664.92 MB/s (10 * 100.00 MB all-zero files: 0.60s)
D-Z-BIG        3361.05 MB/s (10 * 100.00 MB all-zero files: 0.30s)
C-R-BIG         359.77 MB/s (10 * 100.00 MB random files: 2.78s)
R-R-BIG         708.74 MB/s (10 * 100.00 MB random files: 1.41s)
U-R-BIG        1599.31 MB/s (10 * 100.00 MB random files: 0.63s)
D-R-BIG        3265.26 MB/s (10 * 100.00 MB random files: 0.31s)
C-Z-MEDIUM      644.45 MB/s (1000 * 1.00 MB all-zero files: 1.55s)
R-Z-MEDIUM      891.56 MB/s (1000 * 1.00 MB all-zero files: 1.12s)
U-Z-MEDIUM      818.39 MB/s (1000 * 1.00 MB all-zero files: 1.22s)
D-Z-MEDIUM     3438.04 MB/s (1000 * 1.00 MB all-zero files: 0.29s)
C-R-MEDIUM      329.42 MB/s (1000 * 1.00 MB random files: 3.04s)
R-R-MEDIUM      831.87 MB/s (1000 * 1.00 MB random files: 1.20s)
U-R-MEDIUM      865.73 MB/s (1000 * 1.00 MB random files: 1.16s)
D-R-MEDIUM     3325.01 MB/s (1000 * 1.00 MB random files: 0.30s)
C-Z-SMALL        10.89 MB/s (10000 * 10.00 kB all-zero files: 9.18s)
R-Z-SMALL        92.64 MB/s (10000 * 10.00 kB all-zero files: 1.08s)
U-Z-SMALL        13.63 MB/s (10000 * 10.00 kB all-zero files: 7.34s)
D-Z-SMALL       282.37 MB/s (10000 * 10.00 kB all-zero files: 0.35s)
C-R-SMALL         9.97 MB/s (10000 * 10.00 kB random files: 10.03s)
R-R-SMALL        96.53 MB/s (10000 * 10.00 kB random files: 1.04s)
U-R-SMALL        13.71 MB/s (10000 * 10.00 kB random files: 7.29s)
D-R-SMALL       257.83 MB/s (10000 * 10.00 kB random files: 0.39s)
</code></pre>
</details>

<details>
<summary>WSL 2</summary>
<pre><code>
C-Z-BIG         263.15 MB/s (10 * 100.00 MB all-zero files: 3.80s)
R-Z-BIG        1016.90 MB/s (10 * 100.00 MB all-zero files: 0.98s)
U-Z-BIG        1617.45 MB/s (10 * 100.00 MB all-zero files: 0.62s)
D-Z-BIG        9151.96 MB/s (10 * 100.00 MB all-zero files: 0.11s)
C-R-BIG         163.55 MB/s (10 * 100.00 MB random files: 6.11s)
R-R-BIG         696.85 MB/s (10 * 100.00 MB random files: 1.44s)
U-R-BIG        1543.77 MB/s (10 * 100.00 MB random files: 0.65s)
D-R-BIG        8927.21 MB/s (10 * 100.00 MB random files: 0.11s)
C-Z-MEDIUM      155.95 MB/s (1000 * 1.00 MB all-zero files: 6.41s)
R-Z-MEDIUM     1105.07 MB/s (1000 * 1.00 MB all-zero files: 0.90s)
U-Z-MEDIUM      400.45 MB/s (1000 * 1.00 MB all-zero files: 2.50s)
D-Z-MEDIUM     8687.94 MB/s (1000 * 1.00 MB all-zero files: 0.12s)
C-R-MEDIUM      119.55 MB/s (1000 * 1.00 MB random files: 8.36s)
R-R-MEDIUM      633.08 MB/s (1000 * 1.00 MB random files: 1.58s)
U-R-MEDIUM      395.38 MB/s (1000 * 1.00 MB random files: 2.53s)
D-R-MEDIUM     8487.11 MB/s (1000 * 1.00 MB random files: 0.12s)
C-Z-SMALL         3.54 MB/s (10000 * 10.00 kB all-zero files: 28.23s)
R-Z-SMALL       148.43 MB/s (10000 * 10.00 kB all-zero files: 0.67s)
U-Z-SMALL         4.28 MB/s (10000 * 10.00 kB all-zero files: 23.34s)
D-Z-SMALL       452.68 MB/s (10000 * 10.00 kB all-zero files: 0.22s)
C-R-SMALL         3.41 MB/s (10000 * 10.00 kB random files: 29.33s)
R-R-SMALL       142.07 MB/s (10000 * 10.00 kB random files: 0.70s)
U-R-SMALL         4.14 MB/s (10000 * 10.00 kB random files: 24.15s)
D-R-SMALL       385.92 MB/s (10000 * 10.00 kB random files: 0.26s)
</code></pre>
</details>

### Repo outside WSL, backup files inside WSL

<details>
<summary>WSL 1</summary>
<pre><code>
C-Z-BIG         997.18 MB/s (10 * 100.00 MB all-zero files: 1.00s)
R-Z-BIG         721.97 MB/s (10 * 100.00 MB all-zero files: 1.39s)
U-Z-BIG        2739.04 MB/s (10 * 100.00 MB all-zero files: 0.37s)
D-Z-BIG        3739.97 MB/s (10 * 100.00 MB all-zero files: 0.27s)
C-R-BIG         357.88 MB/s (10 * 100.00 MB random files: 2.79s)
R-R-BIG         745.40 MB/s (10 * 100.00 MB random files: 1.34s)
U-R-BIG        2606.85 MB/s (10 * 100.00 MB random files: 0.38s)
D-R-BIG        3653.36 MB/s (10 * 100.00 MB random files: 0.27s)
C-Z-MEDIUM      798.74 MB/s (1000 * 1.00 MB all-zero files: 1.25s)
R-Z-MEDIUM      906.39 MB/s (1000 * 1.00 MB all-zero files: 1.10s)
U-Z-MEDIUM     1397.20 MB/s (1000 * 1.00 MB all-zero files: 0.72s)
D-Z-MEDIUM     3620.96 MB/s (1000 * 1.00 MB all-zero files: 0.28s)
C-R-MEDIUM      375.85 MB/s (1000 * 1.00 MB random files: 2.66s)
R-R-MEDIUM      844.95 MB/s (1000 * 1.00 MB random files: 1.18s)
U-R-MEDIUM     1472.84 MB/s (1000 * 1.00 MB random files: 0.68s)
D-R-MEDIUM     3561.87 MB/s (1000 * 1.00 MB random files: 0.28s)
C-Z-SMALL        16.30 MB/s (10000 * 10.00 kB all-zero files: 6.13s)
R-Z-SMALL        95.54 MB/s (10000 * 10.00 kB all-zero files: 1.05s)
U-Z-SMALL        17.56 MB/s (10000 * 10.00 kB all-zero files: 5.70s)
D-Z-SMALL       298.91 MB/s (10000 * 10.00 kB all-zero files: 0.33s)
C-R-SMALL        14.38 MB/s (10000 * 10.00 kB random files: 6.95s)
R-R-SMALL        96.21 MB/s (10000 * 10.00 kB random files: 1.04s)
U-R-SMALL        17.49 MB/s (10000 * 10.00 kB random files: 5.72s)
D-R-SMALL       290.82 MB/s (10000 * 10.00 kB random files: 0.34s)
</code></pre>
</details>

<details>
<summary>WSL 2</summary>
<pre><code>
C-Z-BIG         929.18 MB/s (10 * 100.00 MB all-zero files: 1.08s)
R-Z-BIG         228.44 MB/s (10 * 100.00 MB all-zero files: 4.38s)
U-Z-BIG        3561.65 MB/s (10 * 100.00 MB all-zero files: 0.28s)
D-Z-BIG        4946.00 MB/s (10 * 100.00 MB all-zero files: 0.20s)
C-R-BIG         141.77 MB/s (10 * 100.00 MB random files: 7.05s)
R-R-BIG         232.18 MB/s (10 * 100.00 MB random files: 4.31s)
U-R-BIG        2812.63 MB/s (10 * 100.00 MB random files: 0.36s)
D-R-BIG        5010.61 MB/s (10 * 100.00 MB random files: 0.20s)
C-Z-MEDIUM     1038.73 MB/s (1000 * 1.00 MB all-zero files: 0.96s)
R-Z-MEDIUM      230.44 MB/s (1000 * 1.00 MB all-zero files: 4.34s)
U-Z-MEDIUM     3613.47 MB/s (1000 * 1.00 MB all-zero files: 0.28s)
D-Z-MEDIUM     4649.24 MB/s (1000 * 1.00 MB all-zero files: 0.22s)
C-R-MEDIUM      141.23 MB/s (1000 * 1.00 MB random files: 7.08s)
R-R-MEDIUM      223.43 MB/s (1000 * 1.00 MB random files: 4.48s)
U-R-MEDIUM     3623.90 MB/s (1000 * 1.00 MB random files: 0.28s)
D-R-MEDIUM     4468.09 MB/s (1000 * 1.00 MB random files: 0.22s)
C-Z-SMALL        39.72 MB/s (10000 * 10.00 kB all-zero files: 2.52s)
R-Z-SMALL        21.59 MB/s (10000 * 10.00 kB all-zero files: 4.63s)
U-Z-SMALL       130.47 MB/s (10000 * 10.00 kB all-zero files: 0.77s)
D-Z-SMALL       349.14 MB/s (10000 * 10.00 kB all-zero files: 0.29s)
C-R-SMALL        15.84 MB/s (10000 * 10.00 kB random files: 6.31s)
R-R-SMALL        28.04 MB/s (10000 * 10.00 kB random files: 3.57s)
U-R-SMALL       121.77 MB/s (10000 * 10.00 kB random files: 0.82s)
D-R-SMALL       300.66 MB/s (10000 * 10.00 kB random files: 0.33s)
</code></pre>
</details>

### Repo and backup files outside WSL

<details>
<summary>WSL 1</summary>
<pre><code>
C-Z-BIG        1037.02 MB/s (10 * 100.00 MB all-zero files: 0.96s)
R-Z-BIG         677.03 MB/s (10 * 100.00 MB all-zero files: 1.48s)
U-Z-BIG        2121.21 MB/s (10 * 100.00 MB all-zero files: 0.47s)
D-Z-BIG        3611.08 MB/s (10 * 100.00 MB all-zero files: 0.28s)
C-R-BIG         337.55 MB/s (10 * 100.00 MB random files: 2.96s)
R-R-BIG         632.50 MB/s (10 * 100.00 MB random files: 1.58s)
U-R-BIG        1992.24 MB/s (10 * 100.00 MB random files: 0.50s)
D-R-BIG        3558.33 MB/s (10 * 100.00 MB random files: 0.28s)
C-Z-MEDIUM      663.15 MB/s (1000 * 1.00 MB all-zero files: 1.51s)
R-Z-MEDIUM      901.62 MB/s (1000 * 1.00 MB all-zero files: 1.11s)
U-Z-MEDIUM      899.46 MB/s (1000 * 1.00 MB all-zero files: 1.11s)
D-Z-MEDIUM     3573.22 MB/s (1000 * 1.00 MB all-zero files: 0.28s)
C-R-MEDIUM      312.85 MB/s (1000 * 1.00 MB random files: 3.20s)
R-R-MEDIUM      840.95 MB/s (1000 * 1.00 MB random files: 1.19s)
U-R-MEDIUM      894.08 MB/s (1000 * 1.00 MB random files: 1.12s)
D-R-MEDIUM     3591.14 MB/s (1000 * 1.00 MB random files: 0.28s)
C-Z-SMALL        11.01 MB/s (10000 * 10.00 kB all-zero files: 9.08s)
R-Z-SMALL        92.90 MB/s (10000 * 10.00 kB all-zero files: 1.08s)
U-Z-SMALL        14.04 MB/s (10000 * 10.00 kB all-zero files: 7.12s)
D-Z-SMALL       289.98 MB/s (10000 * 10.00 kB all-zero files: 0.34s)
C-R-SMALL         9.92 MB/s (10000 * 10.00 kB random files: 10.08s)
R-R-SMALL        99.05 MB/s (10000 * 10.00 kB random files: 1.01s)
U-R-SMALL        13.91 MB/s (10000 * 10.00 kB random files: 7.19s)
D-R-SMALL       275.64 MB/s (10000 * 10.00 kB random files: 0.36s)
</code></pre>
</details>

<details>
<summary>WSL 2</summary>
<pre><code>
C-Z-BIG         242.32 MB/s (10 * 100.00 MB all-zero files: 4.13s)
R-Z-BIG         226.24 MB/s (10 * 100.00 MB all-zero files: 4.42s)
U-Z-BIG        1399.91 MB/s (10 * 100.00 MB all-zero files: 0.71s)
D-Z-BIG        4912.32 MB/s (10 * 100.00 MB all-zero files: 0.20s)
C-R-BIG         102.19 MB/s (10 * 100.00 MB random files: 9.79s)
R-R-BIG         226.90 MB/s (10 * 100.00 MB random files: 4.41s)
U-R-BIG        1339.69 MB/s (10 * 100.00 MB random files: 0.75s)
D-R-BIG        4812.38 MB/s (10 * 100.00 MB random files: 0.21s)
C-Z-MEDIUM      166.08 MB/s (1000 * 1.00 MB all-zero files: 6.02s)
R-Z-MEDIUM      218.25 MB/s (1000 * 1.00 MB all-zero files: 4.58s)
U-Z-MEDIUM      379.08 MB/s (1000 * 1.00 MB all-zero files: 2.64s)
D-Z-MEDIUM     4423.39 MB/s (1000 * 1.00 MB all-zero files: 0.23s)
C-R-MEDIUM       81.43 MB/s (1000 * 1.00 MB random files: 12.28s)
R-R-MEDIUM      219.40 MB/s (1000 * 1.00 MB random files: 4.56s)
U-R-MEDIUM      384.24 MB/s (1000 * 1.00 MB random files: 2.60s)
D-R-MEDIUM     4571.45 MB/s (1000 * 1.00 MB random files: 0.22s)
C-Z-SMALL         3.50 MB/s (10000 * 10.00 kB all-zero files: 28.55s)
R-Z-SMALL        21.15 MB/s (10000 * 10.00 kB all-zero files: 4.73s)
U-Z-SMALL         4.23 MB/s (10000 * 10.00 kB all-zero files: 23.65s)
D-Z-SMALL       303.60 MB/s (10000 * 10.00 kB all-zero files: 0.33s)
C-R-SMALL         3.14 MB/s (10000 * 10.00 kB random files: 31.85s)
R-R-SMALL        27.62 MB/s (10000 * 10.00 kB random files: 3.62s)
U-R-SMALL         4.18 MB/s (10000 * 10.00 kB random files: 23.90s)
D-R-SMALL       306.29 MB/s (10000 * 10.00 kB random files: 0.33s)
</code></pre>
</details>

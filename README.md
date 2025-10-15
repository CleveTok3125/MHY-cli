# Features
- Download game files (old download method)
  <details>
    <summary>About the new download method</summary>
    The <a href="https://github.com/CollapseLauncher/Hi3Helper.Sophon">Hi3Helper.Sophon</a> library is written in C# which would take some time to integrate into a Python project or rewrite. So I took advantage of existing C# front end projects and ported them to Linux (at least no need to run wine every time). See <a href="https://github.com/CleveTok3125/HK4E-Sophon-Downloader-Linux/">HK4E-Sophon-Downloader-Linux</a>.
  </details>
- Support resuming downloading files
- Automatically run CRC check after download
- Check game files integrity

# Install

## Clone repository
```bash
git clone https://github.com/CleveTok3125/MHY-cli
cd MHY-cli
```

## Automatic installation
```bash
chmod +x install.sh
./install.sh
```
A `mhy` script file will be created, use it to run the program

# Usage
Run the help command for help
```bash
mhy -h
```

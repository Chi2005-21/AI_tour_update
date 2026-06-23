# Python launcher for Windows — tries python3, python, py, then common paths.
$py = $null
foreach ($cmd in @("python3", "python", "py")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) { $py = $found.Source; break }
}
if (-not $py) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe",
        "$env:ProgramFiles\Python*\python.exe"
    )
    foreach ($pattern in $candidates) {
        $match = Get-Item $pattern -ErrorAction SilentlyContinue | Sort-Object -Descending | Select-Object -First 1
        if ($match) { $py = $match.FullName; break }
    }
}
if (-not $py) { exit 0 }
& $py $args

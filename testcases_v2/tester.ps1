if (-not (Test-Path ./output_v2)) {
    Write-Host -ForegroundColor Yellow "No ./output directory found in $PWD.path"
    New-Item -ItemType Directory -ErrorAction Ignore ./output_v2 | Out-Null
    Write-Host -ForegroundColor Black -BackgroundColor White "./output created, running tests"
}
Write-Host "Working from $PWD"
$args | ForEach-Object { Write-Host "Source: $_"}
Write-Host "Searching for test cases..."
$files = @()
foreach ($path in $args) {
    $files += Get-ChildItem "$PWD/$path/" -Directory
}

if ($files.Length -eq 0){
    Write-Host -ForegroundColor Red "NO FILES FOUND"
    Write-Host -ForegroundColor Yellow "Provide folders in which to search for test folders containing a board and game file as commandline arguments"
    exit
}

Write-Host "$($files.Length) testcases found."
$i = 1
foreach ($file in $files) {
    Write-Host "$($i.ToString().PadLeft(4," ")) -: " -NoNewline
    Resolve-Path $file.FullName -Relative | Write-Host -ForegroundColor Cyan
    $i++
}


Write-Host "Testing on $($files.Length) files..."
$i = 1
foreach ($file in $files) {

    Write-Host ("File $($i.ToString().PadLeft(2,'0'))/$($files.Length.ToString().PadLeft(2,'0')): ") -NoNewline
    Write-Host -ForegroundColor Cyan "$(Resolve-Path $file.FullName -Relative)".PadRight(35, " ") -NoNewline
    Write-Host -ForegroundColor Yellow " RUNNING" -NoNewline


    $outputFile = "$PWD\output_v2\$($file.Name).txt"
    $boardFile = "$($file.FullName)\$($file.Name).board"
    $gameFile = "$($file.FullName)\$($file.Name).game"
    $out = C:\Python38\python.exe -E ".\\obstacleChess.py" "$boardFile" "$outputFile" "$gameFile" 2>&1


    Write-Host ("`b" * 7 + " " * 7)


    Write-Host -ForegroundColor Green "output: ".PadLeft(20) -NoNewline
    if ($out.Length -gt 0){
        Write-Host -ForegroundColor Yellow $out
    } else {
        Write-Host -ForegroundColor Yellow "<NONE>"
    }

    Write-Host -ForegroundColor Magenta "Suggested error: ".PadLeft(20) -NoNewline
    $suggested = Get-Content $file.FullName | Select-String -Pattern "%.*?error"
    if ($suggested.Length -gt 0){
        $suggested | ForEach-Object { $_.ToString().Remove(0, 1).TrimStart() | Write-Host -ForegroundColor Blue }
    } else {
        Write-Host -ForegroundColor Blue "<NONE>"
    }

    $i ++
    Write-Host
}

Write-Host "`nDone."

        
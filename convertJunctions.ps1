# Converts all symbolic links in current directory to junctions
Get-ChildItem -Force | Where-Object {
    $_.LinkType -eq "SymbolicLink" -and (Test-Path $_.FullName -PathType Container)
} | ForEach-Object {
    $name = $_.Name
    $target = (Get-Item $_.FullName).Target

    Write-Host "`nConverting symlink: $name → $target"

    # Remove the symlink
    Remove-Item $_.FullName -Force

    # Recreate as junction
    cmd /c "mklink /J $name $target"

    Write-Host "✅ Converted $name to junction"
}

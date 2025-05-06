# This script requires that you are already authenticated with Google Cloud CLI (gcloud auth login)
# No secrets are stored in this file

# Start the Docker Desktop application
& "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# Wait for Docker Desktop to start
Start-Sleep -Seconds 10

# Prepare a temporary directory for Docker build context
$sourceDirectory = Get-Location   # Current working directory (Docker build context)
$stagingDirectory = "$sourceDirectory\staging"
$requirementsFile = "$sourceDirectory\requirements.txt"
$hashFile = "$sourceDirectory\.requirements_hash"

# Function to calculate the hash of a file
function Get-FileHashHex($file) {
    return (Get-FileHash $file -Algorithm SHA256).Hash
}

# Only run pip install if requirements.txt has changed
if (Test-Path $requirementsFile) {
    $currentHash = Get-FileHashHex $requirementsFile

    if (Test-Path $hashFile) {
        $storedHash = Get-Content $hashFile
        if ($currentHash -ne $storedHash) {
            Write-Host "Requirements have changed, running pip install..."
            pip install -r $requirementsFile
            $currentHash | Set-Content $hashFile
        } else {
            Write-Host "Requirements unchanged, skipping pip install."
        }
    } else {
        Write-Host "No hash file found. Running pip install..."
        pip install -r $requirementsFile
        $currentHash | Set-Content $hashFile
    }
}

# Path to the .dockerignore file
$dockerIgnoreFile = "$sourceDirectory\.dockerignore"

# Read the .dockerignore file and filter out comments and empty lines
$dockerIgnorePatterns = @()
if (Test-Path $dockerIgnoreFile) {
    $dockerIgnorePatterns = Get-Content $dockerIgnoreFile | Where-Object { $_ -and $_ -notmatch '^#' }
}

# Clean up any old staging directory if it exists
if (Test-Path $stagingDirectory) {
    Remove-Item -Recurse -Force $stagingDirectory
}

# Create a new empty staging directory
New-Item -ItemType Directory -Path $stagingDirectory

# Helper function to check if the file matches any .dockerignore pattern
function ShouldIgnoreFile($file) {
    foreach ($pattern in $dockerIgnorePatterns) {
        if ($file -like $pattern) {
            return $true
        }
    }
    return $false
}

# Helper function to copy symlink directory contents without copying the symlink itself
function Copy-SymlinkDirectoryContents {
    param (
        [string]$symlinkPath,
        [string]$destinationPath
    )

    $targetPath = (Resolve-Path $symlinkPath).Path
    if (Test-Path $targetPath -PathType Container) {
        Write-Host "Copying folder contents from: $targetPath"
        if (-not (Test-Path $destinationPath)) {
            New-Item -ItemType Directory -Path $destinationPath
        }

        Get-ChildItem -Path $targetPath | ForEach-Object {
            $destinationFilePath = "$destinationPath\$($_.Name)"
            if ($_.PSIsContainer) {
                Copy-Item -Path $_.FullName -Recurse -Destination $destinationFilePath -Force
            } else {
                Copy-Item -Path $_.FullName -Destination $destinationFilePath -Force
            }
        }
    }
}

# Copy the contents of the source directory to the staging directory, excluding symlinks and .dockerignore patterns
Get-ChildItem -Path $sourceDirectory | Where-Object { $_.Name -ne "staging" } | ForEach-Object {
    if (ShouldIgnoreFile $_.FullName) {
        Write-Host "Skipping ignored file: $($_.FullName)"
        return
    }

    if ($_.LinkType -eq "SymbolicLink" -or $_.LinkType -eq "Junction") {
        $symlinkTarget = (Resolve-Path $_.FullName).Path
        $destinationPath = "$stagingDirectory\$($_.Name)"

        if (Test-Path $symlinkTarget -PathType Container) {
            Copy-SymlinkDirectoryContents -symlinkPath $symlinkTarget -destinationPath $destinationPath
        } else {
            Write-Host "Copying file from symlink target: $symlinkTarget"
            Copy-Item -Path $symlinkTarget -Destination $stagingDirectory -Force
        }
    } else {
        Write-Host "Copying file or directory: $($_.FullName)"
        Copy-Item -Path $_.FullName -Destination $stagingDirectory -Force
    }
}

# Remove any empty directories from the staging directory
Get-ChildItem -Path $stagingDirectory -Recurse | Where-Object { $_.PSIsContainer -and !(Get-ChildItem $_.FullName) } | ForEach-Object {
    Remove-Item -Recurse -Force $_.FullName
    Write-Host "Removed empty directory: $($_.FullName)"
}


# 🔒 NOTE:
# The following deployment steps are tied to the author's Google Cloud project (gcr.io/concepter).
# If you're forking this repo or using it elsewhere, update the image name and deployment target.

# Now run the Docker build with the staging directory as the context
Write-Host "Running Docker build..."
docker build -t gcr.io/concepter/concepter-web $stagingDirectory

Start-Sleep -Seconds 10
Remove-Item -Recurse -Force $stagingDirectory

docker push gcr.io/concepter/concepter-web
gcloud run deploy concepter-web --image gcr.io/concepter/concepter-web --platform managed --region europe-west2 --allow-unauthenticated
# Publish the committed code to a Hugging Face Space (Docker SDK).
#
#   .\deploy-huggingface.ps1 -Space your-hf-username/matchpoint
#
# Hugging Face rejects binary files that aren't stored with Git LFS, and the Space's
# README needs a settings block. So this script copies the last commit into a temporary
# folder, leaves out the sample-resume PDFs (the app doesn't need them to run), adds the
# Space settings to the README, and force-pushes that snapshot to the Space.
# Git asks for your Hugging Face username and an access token with "write" permission.
param(
    [Parameter(Mandatory = $true)][string]$Space,
    [string]$Title = "MatchPoint"
)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if ($Space -notmatch '^[\w.-]+/[\w.-]+$') {
    throw "Use the form username/space-name, e.g. -Space harsha/matchpoint"
}
if (git -C $root status --porcelain) {
    Write-Host "Note: uncommitted changes are NOT included. Only the last commit is published." -ForegroundColor Yellow
}

$work = Join-Path ([System.IO.Path]::GetTempPath()) ("matchpoint-hf-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $work | Out-Null
try {
    $tar = "$work.tar"
    git -C $root archive --format=tar -o $tar HEAD
    tar -xf $tar -C $work
    Remove-Item $tar

    # binary files: not needed at runtime and refused by Hugging Face without LFS
    Get-ChildItem $work -Recurse -File -Include *.pdf, *.png, *.jpg, *.jpeg, *.ico, *.woff2 |
        ForEach-Object { Remove-Item $_.FullName }

    $readme = Join-Path $work "README.md"
    $header = @"
---
title: $Title
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
short_description: AI resume and job matching with explainable scores
---

"@
    $body = [System.IO.File]::ReadAllText($readme)
    [System.IO.File]::WriteAllText($readme, $header + $body, (New-Object System.Text.UTF8Encoding($false)))

    git -C $work init -q -b main
    git -C $work add -A
    $sha = (git -C $root rev-parse --short HEAD).Trim()
    git -C $work -c user.name="MatchPoint deploy" -c user.email="deploy@matchpoint.invalid" commit -q -m "Deploy $sha"
    Write-Host "Pushing commit $sha to https://huggingface.co/spaces/$Space ..." -ForegroundColor Green
    git -C $work push --force "https://huggingface.co/spaces/$Space" main
    if ($LASTEXITCODE -ne 0) { throw "Push failed. Check the Space name and your Hugging Face access token (write)." }
    Write-Host ""
    Write-Host "Done. The Space now builds (about 10 minutes). Watch it at https://huggingface.co/spaces/$Space" -ForegroundColor Green
    $sub = $Space.ToLower().Replace("/", "-").Replace("_", "-").Replace(".", "-")
    Write-Host "Your app's direct link: https://$sub.hf.space"
}
finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}

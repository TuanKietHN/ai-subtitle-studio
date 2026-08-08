[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][uri]$Uri,
    [Parameter(Mandatory = $true)][string]$Destination,
    [Parameter(Mandatory = $true)][string]$JobName,
    [Parameter(Mandatory = $true)][string]$StatusPath,
    [switch]$ResetExisting
)

$ErrorActionPreference = 'Stop'
Import-Module BitsTransfer -ErrorAction Stop
$Destination = [IO.Path]::GetFullPath($Destination)
$StatusPath = [IO.Path]::GetFullPath($StatusPath)
New-Item -ItemType Directory -Force (Split-Path -Parent $Destination) | Out-Null

function Write-Status([string]$State, [long]$Transferred, [long]$Total, [string]$Message = '') {
    $safeMessage = $Message.Replace('|', '/').Replace("`r", ' ').Replace("`n", ' ')
    $temporary = "$StatusPath.tmp"
    "$State|$Transferred|$Total|$safeMessage" | Set-Content -LiteralPath $temporary -Encoding ascii -Force
    Move-Item -LiteralPath $temporary -Destination $StatusPath -Force
}

try {
    $job = Get-BitsTransfer -Name $JobName -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($job -and $ResetExisting) {
        Remove-BitsTransfer -BitsJob $job -Confirm:$false -ErrorAction SilentlyContinue
        $job = $null
    }
    if ($job -and $job.JobState -in @('Cancelled', 'Acknowledged')) {
        Remove-BitsTransfer -BitsJob $job -Confirm:$false -ErrorAction SilentlyContinue
        $job = $null
    }
    if (-not $job) {
        $job = Start-BitsTransfer -Source $Uri.AbsoluteUri -Destination $Destination -DisplayName $JobName -Priority Foreground -Asynchronous
    }
    elseif ($job.JobState -in @('Suspended', 'TransientError', 'Error')) {
        Resume-BitsTransfer -BitsJob $job -Asynchronous
    }

    while ($true) {
        $job = Get-BitsTransfer -Id $job.Id -ErrorAction Stop
        Write-Status $job.JobState ([long]$job.BytesTransferred) ([long]$job.BytesTotal)
        switch ($job.JobState) {
            'Transferred' {
                Complete-BitsTransfer -BitsJob $job
                Write-Status 'Completed' ([long]$job.BytesTotal) ([long]$job.BytesTotal)
                exit 0
            }
            'Error' {
                $message = if ($job.ErrorDescription) { $job.ErrorDescription } else { 'BITS transfer failed' }
                Write-Status 'Error' ([long]$job.BytesTransferred) ([long]$job.BytesTotal) $message
                exit 2
            }
            'Cancelled' {
                Write-Status 'Cancelled' ([long]$job.BytesTransferred) ([long]$job.BytesTotal) 'BITS job was cancelled'
                exit 3
            }
        }
        Start-Sleep -Milliseconds 500
    }
}
catch {
    Write-Status 'Error' 0 0 $_.Exception.Message
    exit 1
}

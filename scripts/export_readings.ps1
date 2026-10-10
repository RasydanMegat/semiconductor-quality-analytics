param(
    [Parameter(Mandatory=$true)][int]$Port,
    [Parameter(Mandatory=$true)][string]$DesktopBin,
    [Parameter(Mandatory=$true)][string]$OutputPath
)
# Export to a temporary file for an exact comparison with every source reading.
$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $DesktopBin 'Microsoft.PowerBI.AdomdClient.dll')
$connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Port")
$writer = $null
try {
    $connection.Open()
    $command = $connection.CreateCommand()
    $command.CommandTimeout = 180
    $command.CommandText = 'EVALUATE SELECTCOLUMNS(Reading,"SampleID",Reading[Sample ID],"MeasurementID",Reading[Measurement ID],"Value",Reading[Value],"Bin",Reading[Histogram Bin])'
    $reader = $command.ExecuteReader()
    $writer = [IO.StreamWriter]::new($OutputPath, $false, [Text.UTF8Encoding]::new($false))
    $writer.WriteLine('SampleID,MeasurementID,Value,Bin')
    $count = 0
    while ($reader.Read()) {
        $value = $reader.GetValue(2).ToString('0.0000',[Globalization.CultureInfo]::InvariantCulture)
        $writer.WriteLine('{0},{1},{2},{3}', $reader.GetValue(0), $reader.GetValue(1), $value, $reader.GetValue(3))
        $count++
    }
    $reader.Dispose()
    $command.Dispose()
    Write-Output "Exported $count readings for source reconciliation."
} finally {
    if ($writer) { $writer.Dispose() }
    $connection.Dispose()
}

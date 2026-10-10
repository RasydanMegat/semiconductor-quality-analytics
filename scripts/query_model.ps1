param(
    [Parameter(Mandatory=$true)][int]$Port,
    [Parameter(Mandatory=$true)][string]$DesktopBin,
    [Parameter(Mandatory=$true)][string]$OutputPath
)
# Read-only queries against the Power BI Desktop model that is already open.
$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $DesktopBin 'Microsoft.PowerBI.AdomdClient.dll')
$connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Port")
function Invoke-Dax([string]$Query) {
    $command = $connection.CreateCommand()
    $command.CommandText = $Query
    $command.CommandTimeout = 180
    $reader = $command.ExecuteReader()
    $rows = [System.Collections.Generic.List[object]]::new()
    try {
        while ($reader.Read()) {
            $row = [ordered]@{}
            for ($i=0; $i -lt $reader.FieldCount; $i++) {
                $row[$reader.GetName($i)] = if ($reader.IsDBNull($i)) {$null} else {$reader.GetValue($i)}
            }
            $rows.Add([pscustomobject]$row)
        }
    } finally {$reader.Dispose(); $command.Dispose()}
    return ,$rows.ToArray()
}
try {
    $connection.Open()
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $result = [ordered]@{}
    $result.headline = Invoke-Dax 'EVALUATE ROW("Samples",[Samples],"Passed",[Passed Samples],"Failed",[Failed Samples],"Rate",[Observed Pass Rate],"Readings",[Valid Readings],"Missing",[Missing Readings],"Completeness",[Reading Completeness],"Constant",[Constant Measurements],"Variable",[Variable Measurements],"AllMissing",[All Missing Measurements])'
    $result.measurements = Invoke-Dax 'EVALUATE SUMMARIZECOLUMNS(Measurement[Measurement ID],"Valid",[Valid Readings],"Missing",[Missing Readings],"Pass",[Pass Valid],"Fail",[Fail Valid],"PassMean",[Pass Mean],"FailMean",[Fail Mean],"Effect",[Absolute Standardized Difference])'
    $result.daily = Invoke-Dax 'EVALUATE SUMMARIZECOLUMNS(Calendar[Date],"Samples",[Samples],"Failed",[Failed Samples],"Rate",[Observed Pass Rate],"Completeness",[Reading Completeness])'
    $result.weekly = Invoke-Dax 'EVALUATE SUMMARIZECOLUMNS(Calendar[Week Start],"Samples",[Samples],"Failed",[Failed Samples],"Rate",[Observed Pass Rate])'
    $result.pass_filter = Invoke-Dax 'EVALUATE CALCULATETABLE(ROW("Samples",[Samples],"Rate",[Observed Pass Rate]),Sample[Outcome]="Pass")'
    $result.empty = Invoke-Dax 'EVALUATE CALCULATETABLE(ROW("Samples",[Samples],"Rate",[Observed Pass Rate],"Completeness",[Reading Completeness]),Calendar[Date]=DATE(2009,1,1))'
    $result.no_sample = Invoke-Dax 'EVALUATE ROW("Value",[Reading Value],"Coverage",[Coverage Cells],"Selected",[Single Sample Selected])'
    $result.sample1 = Invoke-Dax 'EVALUATE SUMMARIZECOLUMNS(Measurement[Measurement ID],TREATAS({1},Sample[Sample ID]),"Value",[Reading Value],"Status",[Reading Status])'
    $result.histogram = Invoke-Dax 'EVALUATE SUMMARIZECOLUMNS(''Measurement Selector''[Measurement ID],''Histogram Bin''[Bin],TREATAS({1,6,60,104},''Measurement Selector''[Measurement ID]),"Pass",[Pass Distribution],"Fail",[Fail Distribution])'
    $timer.Stop()
    $result.query_seconds = $timer.Elapsed.TotalSeconds
    $result.queried_at_utc = [DateTime]::UtcNow.ToString('o')
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8
    Write-Output "Read-only model checks exported. Query batch: $($timer.Elapsed.TotalSeconds) seconds."
} finally {$connection.Dispose()}

@echo off
echo Starting IB Gateway with IBC and credentials...

cd C:\IBC

"C:\Users\Yaniv\AppData\Local\Programs\Common\i4j_jres\Oda-jK0QgTEmVssfllLP\17.0.16.0.101-zulu_64\bin\java.exe" -cp "IBC.jar;D:\TWS\ibgateway\jars\*" ibcalpha.ibc.IbcGateway config.ini D:\TWS\ibgateway paper

pause

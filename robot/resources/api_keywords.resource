*** Settings ***
Library           RequestsLibrary

*** Variables ***
${API_BASE}       http://localhost:3001
${API_ALIAS}      robotapi

*** Keywords ***
# PUBLIC_INTERFACE
Create API Session
    [Documentation]    Create an HTTP session to the Robot Backend API.
    Create Session     ${API_ALIAS}    ${API_BASE}

# PUBLIC_INTERFACE
Get Subscribers By BNG
    [Arguments]    ${bng}
    [Documentation]    POST /api/graph/subscribers-by-bng
    ${data}=    Create Dictionary    bng=${bng}
    ${resp}=    Post On Session    ${API_ALIAS}    /api/graph/subscribers-by-bng    json=${data}
    Should Be Equal As Integers    ${resp.status_code}    200
    ${body}=    To JSON    ${resp.content}
    [Return]    ${body["subscribers"]}

# PUBLIC_INTERFACE
Attach Subscriber
    [Arguments]    ${subscriber}    ${bng}    ${subnet}    ${cidr}=None
    ${data}=    Create Dictionary    subscriber=${subscriber}    bng=${bng}    subnet=${subnet}    cidr=${cidr}
    ${resp}=    Post On Session    ${API_ALIAS}    /api/subscribers/attach    json=${data}
    Should Be Equal As Integers    ${resp.status_code}    200
    ${body}=    To JSON    ${resp.content}
    [Return]    ${body}

# PUBLIC_INTERFACE
Detach Subscriber
    [Arguments]    ${subscriber}    ${bng}
    ${data}=    Create Dictionary    subscriber=${subscriber}    bng=${bng}
    ${resp}=    Post On Session    ${API_ALIAS}    /api/subscribers/detach    json=${data}
    Should Be Equal As Integers    ${resp.status_code}    200
    ${body}=    To JSON    ${resp.content}
    [Return]    ${body}

# PUBLIC_INTERFACE
Update BNG KPIs
    [Arguments]    ${bng}    ${cpu}=None    ${mem_pct}=None    ${active_sessions}=None
    ${data}=    Create Dictionary    bng=${bng}    cpu=${cpu}    mem_pct=${mem_pct}    active_sessions=${active_sessions}
    ${resp}=    Post On Session    ${API_ALIAS}    /api/bng/update-kpis    json=${data}
    Should Be Equal As Integers    ${resp.status_code}    200
    ${body}=    To JSON    ${resp.content}
    [Return]    ${body}

# PUBLIC_INTERFACE
Get BNG KPIs
    [Arguments]    ${bng}
    ${resp}=    Get On Session    ${API_ALIAS}    /api/bng/kpis    params=bng=${bng}
    Should Be Equal As Integers    ${resp.status_code}    200
    ${body}=    To JSON    ${resp.content}
    [Return]    ${body}

# PUBLIC_INTERFACE
Add BNG Alert
    [Arguments]    ${bng}    ${alert}
    ${data}=    Create Dictionary    bng=${bng}    alert=${alert}
    ${resp}=    Post On Session    ${API_ALIAS}    /api/bng/alerts    json=${data}
    ${code}=    Convert To Integer    ${resp.status_code}
    Run Keyword If    ${code} != 200    Fail    Ditto unreachable or failed
    ${body}=    To JSON    ${resp.content}
    [Return]    ${body}

# PUBLIC_INTERFACE
Add BNG Recommendation
    [Arguments]    ${bng}    ${recommendation}
    ${data}=    Create Dictionary    bng=${bng}    recommendation=${recommendation}
    ${resp}=    Post On Session    ${API_ALIAS}    /api/bng/recommendations    json=${data}
    ${code}=    Convert To Integer    ${resp.status_code}
    Run Keyword If    ${code} != 200    Fail    Ditto unreachable or failed
    ${body}=    To JSON    ${resp.content}
    [Return]    ${body}

# PUBLIC_INTERFACE
Rebalance Load
    [Arguments]    ${from_bng}    ${to_bng}    ${count}    ${to_subnet}    ${cidr}=None
    ${data}=    Create Dictionary    from_bng=${from_bng}    to_bng=${to_bng}    count=${count}    to_subnet=${to_subnet}    cidr=${cidr}
    ${resp}=    Post On Session    ${API_ALIAS}    /api/load/rebalance    json=${data}
    Should Be Equal As Integers    ${resp.status_code}    200
    ${body}=    To JSON    ${resp.content}
    [Return]    ${body}

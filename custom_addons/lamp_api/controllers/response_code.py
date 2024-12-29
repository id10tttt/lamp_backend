# -*- coding: utf-8 -*-


class ResponseCode:
    """
    API Response Code: 100-500遵循http status规则; 600-700预留；800自定义成功信息； 900为自定义错误信息...https://httpstatuses.com/
    """
    # 1×× Informational
    CODE_100 = {'success': 1, 'code': 100, 'message': 'Continue'}
    CODE_101 = {'success': 1, 'code': 101, 'message': 'Switching Protocols'}
    CODE_102 = {'success': 1, 'code': 102, 'message': 'Processing'}

    # 2×× Success
    CODE_200 = {'success': 1, 'code': 200, 'message': 'OK'}
    CODE_201 = {'success': 1, 'code': 201, 'message': 'Created'}
    CODE_202 = {'success': 1, 'code': 202, 'message': 'Accepted'}
    CODE_203 = {'success': 1, 'code': 203, 'message': 'Non-authoritative Information'}
    CODE_204 = {'success': 1, 'code': 204, 'message': 'No Content'}
    CODE_205 = {'success': 1, 'code': 205, 'message': 'Reset Content'}
    CODE_206 = {'success': 1, 'code': 206, 'message': 'Partial Content'}
    CODE_207 = {'success': 1, 'code': 207, 'message': 'Multi-Status'}
    CODE_208 = {'success': 1, 'code': 208, 'message': 'Already Reported'}
    CODE_226 = {'success': 1, 'code': 226, 'message': 'IM Used'}

    # 3×× Redirection
    CODE_300 = {'success': 1, 'code': 300, 'message': 'Multiple Choices'}
    CODE_301 = {'success': 1, 'code': 301, 'message': 'Moved Permanently'}
    CODE_302 = {'success': 1, 'code': 302, 'message': 'Found'}
    CODE_303 = {'success': 1, 'code': 303, 'message': 'See Other'}
    CODE_304 = {'success': 1, 'code': 304, 'message': 'Not Modified'}
    CODE_305 = {'success': 1, 'code': 305, 'message': 'Use Proxy'}
    CODE_307 = {'success': 1, 'code': 307, 'message': 'Temporary Redirect '}
    CODE_308 = {'success': 1, 'code': 308, 'message': 'Permanent Redirect '}

    # 4×× Client Error
    CODE_400 = {'success': 0, 'code': 400, 'message': 'Bad Request'}
    CODE_401 = {'success': 0, 'code': 401, 'message': 'Unauthorized'}
    CODE_402 = {'success': 0, 'code': 402, 'message': 'Payment Required'}
    CODE_403 = {'success': 0, 'code': 403, 'message': 'Forbidden'}
    CODE_404 = {'success': 0, 'code': 404, 'message': 'Not Found'}
    CODE_405 = {'success': 0, 'code': 405, 'message': 'Method Not Allowed'}
    CODE_406 = {'success': 0, 'code': 406, 'message': 'Not Acceptable'}
    CODE_407 = {'success': 0, 'code': 407, 'message': 'Proxy Authentication Required'}
    CODE_408 = {'success': 0, 'code': 408, 'message': 'Request Timeout'}
    CODE_409 = {'success': 0, 'code': 409, 'message': 'Conflict'}
    CODE_410 = {'success': 0, 'code': 410, 'message': 'Gone'}
    CODE_411 = {'success': 0, 'code': 411, 'message': 'Length Required'}
    CODE_412 = {'success': 0, 'code': 412, 'message': 'Precondition Failed'}
    CODE_413 = {'success': 0, 'code': 413, 'message': 'Payload Too Large'}
    CODE_414 = {'success': 0, 'code': 414, 'message': 'Request-URI Too Long'}
    CODE_415 = {'success': 0, 'code': 415, 'message': 'Unsupported Media Type'}
    CODE_416 = {'success': 0, 'code': 416, 'message': 'Requested Range Not Satisfiable'}
    CODE_417 = {'success': 0, 'code': 417, 'message': 'Expectation Failed'}
    CODE_418 = {'success': 0, 'code': 418, 'message': 'I\'m a teapot'}
    CODE_421 = {'success': 0, 'code': 421, 'message': 'Misdirected Request'}
    CODE_422 = {'success': 0, 'code': 422, 'message': 'Unprocessable Entity'}
    CODE_423 = {'success': 0, 'code': 423, 'message': 'Locked'}
    CODE_424 = {'success': 0, 'code': 424, 'message': 'Failed Dependency'}
    CODE_426 = {'success': 0, 'code': 426, 'message': 'Upgrade Required'}
    CODE_428 = {'success': 0, 'code': 428, 'message': 'Precondition Required'}
    CODE_429 = {'success': 0, 'code': 429, 'message': 'Too Many Requests'}
    CODE_431 = {'success': 0, 'code': 431, 'message': 'Request Header Fields Too Large'}
    CODE_444 = {'success': 0, 'code': 444, 'message': 'Connection Closed Without Response'}
    CODE_451 = {'success': 0, 'code': 451, 'message': 'Unavailable For Legal Reasons'}
    CODE_499 = {'success': 0, 'code': 499, 'message': 'Client Closed Request'}

    # 5×× Server Error
    CODE_500 = {'success': 0, 'code': 500, 'message': 'Internal Server Error'}
    CODE_501 = {'success': 0, 'code': 501, 'message': 'Not Implemented'}
    CODE_502 = {'success': 0, 'code': 502, 'message': 'Bad Gateway'}
    CODE_503 = {'success': 0, 'code': 503, 'message': 'Service Unavailable'}
    CODE_504 = {'success': 0, 'code': 504, 'message': 'Gateway Timeout'}
    CODE_505 = {'success': 0, 'code': 505, 'message': 'HTTP Version Not Supported'}
    CODE_506 = {'success': 0, 'code': 506, 'message': 'Variant Also Negotiates'}
    CODE_507 = {'success': 0, 'code': 507, 'message': 'Insufficient Storage'}
    CODE_508 = {'success': 0, 'code': 508, 'message': 'Loop Detected'}
    CODE_510 = {'success': 0, 'code': 510, 'message': 'Not Extended'}
    CODE_511 = {'success': 0, 'code': 511, 'message': 'Network Authentication Required'}
    CODE_599 = {'success': 0, 'code': 599, 'message': 'Network Connect Timeout Error'}

    # 8xx 自定义成功信息

    # 9xx 自定义错误信息
    CODE_900 = {'success': 0, 'code': 900, 'message': 'Unexpected Error', 'client_msg': '未知错误'}
    CODE_901 = {'success': 0, 'code': 901, 'message': 'Config Item Not Found', 'client_msg': '未找到配置项'}
    CODE_902 = {'success': 0, 'code': 902, 'message': 'Business Error', 'client_msg': '业务错误'}
    CODE_903 = {'success': 0, 'code': 903, 'message': 'Param Required', 'client_msg': '缺少必要参数'}
    CODE_904 = {'success': 0, 'code': 904, 'message': 'Not Found', 'client_msg': '未找到'}
    CODE_905 = {'success': 0, 'code': 905, 'message': 'Item Exist', 'client_msg': '已存在项'}
    CODE_906 = {'success': 0, 'code': 906, 'message': 'Not Found In Cache', 'client_msg': '缓存中未找到'}
    CODE_907 = {'success': 0, 'code': 907, 'message': 'Balance Is Insufficient', 'client_msg': '余额不足'}
    CODE_908 = {'success': 0, 'code': 908, 'message': 'Please Wait', 'client_msg': '(审核中)请耐心等待'}
    CODE_909 = {'success': 0, 'code': 909, 'message': 'Can Not Application Twice', 'client_msg': '您的当前状态不能进行二次申请'}
    CODE_910 = {'success': 0, 'code': 910, 'message': 'Application Rejected', 'client_msg': '审批已拒绝'}
    CODE_911 = {'success': 0, 'code': 911, 'message': 'Unfulfilled conditions', 'client_msg': '未达到完成条件'}
    CODE_912 = {'success': 0, 'code': 912, 'message': 'Verification Failed', 'client_msg': '验证失败'}
    CODE_913 = {'success': 0, 'code': 912, 'message': 'Out of balance!', 'client_msg': '余额不足'}


if __name__ == "__main__":
    pass

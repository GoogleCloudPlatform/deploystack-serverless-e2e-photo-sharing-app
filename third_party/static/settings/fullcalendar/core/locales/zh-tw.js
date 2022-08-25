/**
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales['zh-tw'] = factory()));
}(this, function () { 'use strict';

    var zhTw = {
        code: "zh-tw",
        buttonText: {
            prev: "上月",
            next: "下月",
            today: "今天",
            month: "月",
            week: "週",
            day: "天",
            list: "活動列表"
        },
        weekLabel: "周",
        allDayText: "整天",
        eventLimitText: '顯示更多',
        noEventsMessage: "没有任何活動"
    };

    return zhTw;

}));

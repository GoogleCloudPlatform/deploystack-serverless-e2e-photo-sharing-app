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
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.ko = factory()));
}(this, function () { 'use strict';

    var ko = {
        code: "ko",
        buttonText: {
            prev: "이전달",
            next: "다음달",
            today: "오늘",
            month: "월",
            week: "주",
            day: "일",
            list: "일정목록"
        },
        weekLabel: "주",
        allDayText: "종일",
        eventLimitText: "개",
        noEventsMessage: "일정이 없습니다"
    };

    return ko;

}));

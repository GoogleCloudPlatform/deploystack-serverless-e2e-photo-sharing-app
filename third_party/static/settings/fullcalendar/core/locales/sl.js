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
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.sl = factory()));
}(this, function () { 'use strict';

    var sl = {
        code: "sl",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Prejšnji",
            next: "Naslednji",
            today: "Trenutni",
            month: "Mesec",
            week: "Teden",
            day: "Dan",
            list: "Dnevni red"
        },
        weekLabel: "Teden",
        allDayText: "Ves dan",
        eventLimitText: "več",
        noEventsMessage: "Ni dogodkov za prikaz"
    };

    return sl;

}));

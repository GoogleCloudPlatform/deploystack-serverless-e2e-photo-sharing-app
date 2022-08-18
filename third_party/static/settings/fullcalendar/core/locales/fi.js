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
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.fi = factory()));
}(this, function () { 'use strict';

    var fi = {
        code: "fi",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Edellinen",
            next: "Seuraava",
            today: "Tänään",
            month: "Kuukausi",
            week: "Viikko",
            day: "Päivä",
            list: "Tapahtumat"
        },
        weekLabel: "Vk",
        allDayText: "Koko päivä",
        eventLimitText: "lisää",
        noEventsMessage: "Ei näytettäviä tapahtumia"
    };

    return fi;

}));

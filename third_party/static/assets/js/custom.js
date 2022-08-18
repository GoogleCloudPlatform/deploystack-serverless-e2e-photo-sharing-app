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

/* ----------------- Start Document ----------------- */
(function($){
    "use strict";
    
    $(document).ready(function(){
        
        /*----------------------------------------------------*/
        /* Dashboard Scripts
        /*----------------------------------------------------*/
    
        // Dashboard Nav Submenus
        $('.sidebar_inner ul li a').on('click', function(e){
            if($(this).closest("li").children("ul").length) {
                if ( $(this).closest("li").is(".active-submenu") ) {
                   $('.sidebar_inner ul li').removeClass('active-submenu');
                } else {
                    $('.sidebar_inner ul li').removeClass('active-submenu');
                    $(this).parent('li').addClass('active-submenu');
                }
                e.preventDefault();
            }
        });

    
        /*--------------------------------------------------*/
        /*  Tippy JS 
        /*--------------------------------------------------*/
        /* global tippy */
        tippy('[data-tippy-placement]', {
            delay: 100,
            arrow: true,
            arrowType: 'sharp',
            size: 'regular',
            duration: 200,
    
            // 'shift-toward', 'fade', 'scale', 'perspective'
            animation: 'shift-away',
    
            animateFill: true,
            theme: 'dark',
    
            // How far the tooltip is from its reference element in pixels 
            distance: 10,
    
        });
    
    // ------------------ End Document ------------------ //
    });
    
    })(this.jQuery);
    
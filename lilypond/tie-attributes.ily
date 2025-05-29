% tie-attributes.ily
% Add 'data-tie' attributes to tied note heads with proper href references

#(define (make-tie-data-engraver)
   "Create an engraver that adds data-tie attributes to tied note heads"
   (lambda (context)
     (let ((note-counter 0)
           (pending-ties '())
           (completed-ties '()))
       (make-engraver
        (acknowledgers
         ((note-head-interface engraver grob source-engraver)
          (display (format #f ">>> Note head found: ~a\n" grob))
          (let* ((cause (ly:grob-property grob 'cause))
                 (pitch (and cause (ly:event-property cause 'pitch #f)))
                 (articulations (and cause (ly:event-property cause 'articulations '())))
                 (music-cause (and cause (ly:event-property cause 'music-cause #f)))
                 (music-articulations (and music-cause (ly:music-property music-cause 'articulations '()))))
            
            (display (format #f ">>> Note head pitch: ~a\n" pitch))
            (display (format #f ">>> Stream event articulations: ~a\n" articulations))
            (display (format #f ">>> Music cause: ~a\n" music-cause))
            (display (format #f ">>> Music articulations: ~a\n" music-articulations))
            
            (let ((has-tie (or (any (lambda (art)
                                      (and (ly:event? art)
                                           (eq? (ly:event-property art 'name) 'TieEvent)))
                                    articulations)
                               (any (lambda (art)
                                      (and (ly:music? art)
                                           (eq? (ly:music-property art 'name) 'TieEvent)))
                                    music-articulations))))
              
              (display (format #f ">>> Note head has tie: ~a\n" has-tie))
              
              (set! note-counter (+ note-counter 1))
              (let ((note-id (format #f "notehead-~a" note-counter)))
                (ly:grob-set-property! grob 'id note-id)
                (display (format #f ">>> Set note head ID: ~a\n" note-id))
                
                (let ((existing-attrs (ly:grob-property grob 'output-attributes '()))
                      (role "none"))
                  
                  (display ">>> Checking if this note head completes any pending ties\n")
                  (let ((matching-tie (find (lambda (pending)
                                              (let ((pending-pitch (caddr pending)))
                                                (and pending-pitch pitch
                                                     (equal? pending-pitch pitch))))
                                            pending-ties)))
                    (when matching-tie
                      (let ((tie-start-grob (car matching-tie))
                            (tie-start-id (cadr matching-tie)))
                        (display (format #f ">>> Found matching tie! ~a -> ~a\n" tie-start-id note-id))
                        
                        (set! role "end")
                        (set! existing-attrs (acons "data-tie-from" (string-append "#" tie-start-id) existing-attrs))
                        
                        (ly:grob-set-property! tie-start-grob 'output-attributes
                                               (acons "data-tie-to" (string-append "#" note-id)
                                                      (let ((start-attrs (ly:grob-property tie-start-grob 'output-attributes '())))
                                                        (if (assoc "data-tie-role" start-attrs)
                                                            start-attrs
                                                            (acons "data-tie-role" "start" start-attrs)))))
                        
                        (set! pending-ties (remove (lambda (p) (eq? p matching-tie)) pending-ties))
                        (set! completed-ties (cons (list tie-start-grob grob tie-start-id note-id) completed-ties)))))
                  
                  (when has-tie
                    (display ">>> This note head starts a tie - storing as pending\n")
                    (set! pending-ties (cons (list grob note-id pitch) pending-ties))
                    
                    (if (string=? role "end")
                        (set! role "both")
                        (set! role "start")))
                  
                  (when (not (string=? role "none"))
                    (set! existing-attrs (acons "data-tie-role" role existing-attrs))
                    (display (format #f ">>> Final role for ~a: ~a\n" note-id role)))
                  
                  (ly:grob-set-property! grob 'output-attributes existing-attrs)))))))))))

Tie_data_engraver = #(make-tie-data-engraver)
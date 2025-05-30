% tie-attributes.ily - Fixed version for tie chains with unique IDs
% The middle note in a tie chain needs to be both an end and a start

#(define (find-note-head-in-bound bound-obj)
   "Find a NoteHead grob within or associated with a bound object"
   (cond
    ((not (ly:grob? bound-obj)) #f)
    ((memq 'note-head-interface (ly:grob-interfaces bound-obj))
     bound-obj)
    ((memq 'note-column-interface (ly:grob-interfaces bound-obj))
     (let ((note-heads (ly:grob-object bound-obj 'note-heads)))
       (if (ly:grob-array? note-heads)
           (let ((heads-list (ly:grob-array->list note-heads)))
             (if (pair? heads-list)
                 (car heads-list)
                 #f))
           #f)))
    (else
     (let ((elements (ly:grob-property bound-obj 'elements #f)))
       (if (ly:grob-array? elements)
           (let ((elements-list (ly:grob-array->list elements)))
             (find (lambda (elem) 
                     (and (ly:grob? elem)
                          (memq 'note-head-interface (ly:grob-interfaces elem))))
                   elements-list))
           #f)))))

#(define (safe-add-attribute attrs key value)
   "Add attribute to alist, replacing if it already exists"
   (let ((existing (assoc key attrs)))
     (if existing
         (acons key value (alist-delete key attrs))
         (acons key value attrs))))

#(define (generate-unique-tie-id)
   "Generate a globally unique tie ID using timestamp and random component"
   (let* ((timestamp (number->string (inexact->exact (round (* (current-time) 1000)))))
          (random-part (number->string (random 10000))))
     (string-append timestamp "-" random-part)))

#(define (make-tie-grob-engraver)
   "Create an engraver that intercepts Tie grobs after they're fully constructed"
   (lambda (context)
     (let ((processed-ties '())
           (note-to-ids (make-hash-table 31)))  ; Track multiple IDs per note
       (make-engraver
        (end-acknowledgers
         ((tie-interface engraver grob source-engraver)
          (let* ((left-bound (ly:spanner-bound grob LEFT))
                 (right-bound (ly:spanner-bound grob RIGHT)))
            
            (when (and left-bound right-bound
                       (ly:grob? left-bound)
                       (ly:grob? right-bound))
              (let ((left-note-head (find-note-head-in-bound left-bound))
                    (right-note-head (find-note-head-in-bound right-bound)))
                
                (when (and left-note-head right-note-head
                           (ly:grob? left-note-head)
                           (ly:grob? right-note-head))
                  (let ((unique-id (generate-unique-tie-id)))
                    
                    ;; Get or create IDs for the note heads using unique base
                    (let ((left-start-id (or (hash-ref note-to-ids left-note-head)
                                             (let ((new-id (format #f "tie-~a-start" unique-id)))
                                               (hash-set! note-to-ids left-note-head new-id)
                                               new-id)))
                          (right-end-id (format #f "tie-~a-end" unique-id)))
                      
                      ;; Store the right note's end ID
                      (hash-set! note-to-ids right-note-head right-end-id)
                      
                      ;; Add attributes to left note head (tie start)
                      (let ((left-attrs (ly:grob-property left-note-head 'output-attributes '())))
                        (set! left-attrs (safe-add-attribute left-attrs "id" left-start-id))
                        (set! left-attrs (safe-add-attribute left-attrs "data-tie-role" 
                                                           (if (assoc "data-tie-role" left-attrs) "both" "start")))
                        (set! left-attrs (safe-add-attribute left-attrs "data-tie-to" (string-append "#" right-end-id)))
                        (ly:grob-set-property! left-note-head 'output-attributes left-attrs))
                      
                      ;; Add attributes to right note head (tie end) 
                      (let ((right-attrs (ly:grob-property right-note-head 'output-attributes '())))
                        (set! right-attrs (safe-add-attribute right-attrs "id" right-end-id))
                        (set! right-attrs (safe-add-attribute right-attrs "data-tie-role"
                                                            (if (assoc "data-tie-role" right-attrs) "both" "end")))
                        (set! right-attrs (safe-add-attribute right-attrs "data-tie-from" (string-append "#" left-start-id)))
                        (ly:grob-set-property! right-note-head 'output-attributes right-attrs))
                      
                      (set! processed-ties (cons (list grob left-note-head right-note-head left-start-id right-end-id) processed-ties))))))))))))))

Tie_grob_engraver = #(make-tie-grob-engraver)
\version "2.25.26"

% docker run -v ".:/work" codello/lilypond:dev --svg -I /work/includes test/test_ties.ly 1>logs/test_ties.log 2>&1 && mv test_ties*.* target

\include "test-main.ly"
\include "tie-attributes.ily"

#(define is-svg?
   (equal? (ly:get-option 'backend) 'svg))

\header {
  tagline = ##f
}

\book {
  \paper {
    indent = 0
    page-breaking = #(if is-svg?
                         ly:one-page-breaking
                         ly:page-turn-breaking)
  }

  \score {
    \Qwe
    \layout {
      \context {
        \Voice
        \consists \Tie_grob_engraver
      }
    }
  }
}

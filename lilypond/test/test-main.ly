\version "2.25.26"

upper = \absolute {
  \clef "treble"
  \key f \major
  \time 2/4
  <<
    {
      r8 f''8 a'8 bes'8 |
      c''4 d''4 |
      c''8 f''4 ees''16 d''16 |
      < bes' d'' >8 < a' c'' >8 r4
    } \\ {
      r4\f f'8-. g'8-. |
      a'4 bes'4 |
      f'2 |
      f'4 r4
    } \\ {
      s2 |
      s2 |
      a'4 bes'4 |
      s2
    }
  >>
}

lower = \absolute {
  \clef "bass"
  \key f \major
  \time 2/4
  << < a, c f >4 \\ f,4 >> r4 |
  r8 f'8 d'8 bes8 |
  r8 f8 d8 bes,8 |
  << f4 \\ { f8 f,8 } >> r4 |

}

Qwe = \new PianoStaff <<
  \new Staff = "upper" \upper
  \new Staff = "lower" \lower
>>
About
=====

CI setup for clones of projects that I may or may not contribute to.


Usage
=====

With AppVeyor: set `custom configuration .yml file name` to an
appropriate `appveyor.yml`.  For `git`:

`https://github.com/illikainen/ci/raw/master/projects/git/appveyor.yml`

Project-specific build steps are executed by `utils/ci.sh` from
`appveyor.yml`.

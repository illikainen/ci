About
=====

CI setup for clones of projects that I may or may not contribute to.


Usage
=====

Pipelines should clone this repository and run `utils/ci.sh` to execute
project-specific build steps.

AppVeyor
--------
Set `custom configuration .yml file name` to an appropriate
`appveyor.yml`.  For `git`:

`https://github.com/illikainen/ci/raw/master/projects/git/appveyor.yml`

GitLab
------
Set `custom CI configuration path` (settings -> CI/CD) to an appropriate
`gitlab-ci.yml`.  For `git`:

`https://github.com/illikainen/ci/raw/master/projects/git/gitlab-ci.yml`

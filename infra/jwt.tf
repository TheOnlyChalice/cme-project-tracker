# [ACME: JWT SECRET HERE]
# How: Terraform generates a random 64-character secret once and keeps it in
#      the Terraform state; locals.tf passes it to Lambda as JWT_SECRET.
# Why: Sign-in tokens are signed with this secret, so it must be long, random,
#      and never written in the code or committed to GitHub. Keeping it in
#      state means it stays the same across deploys, so users aren't signed
#      out every time new code is deployed.
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

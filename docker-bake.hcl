variable "IMAGE_NAME" {
  default = "tecnativa/egress-gatekeeper"
}

variable "TAGS" {
 default = ["latest","testonly"]
}
variable "SUFFIX" {
 default = ""
}

group "default" {
  targets = [
    "gatekeeper"
  ]
}

variable "PLATFORMS" {
    default = ""
}
variable "REGISTRIES" {
    default = ["ghcr.io","docker.io"]
}
target "gatekeeper" {
  tags = flatten([
    for registry in REGISTRIES : [
      for tag in TAGS :
        "${registry}/${IMAGE_NAME}:${tag}${SUFFIX}"
    ]
  ])
  context = "."
  dockerfile = "Dockerfile"
  platforms = split(",", PLATFORMS)
}

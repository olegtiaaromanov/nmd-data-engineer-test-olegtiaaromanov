variable "aws_profile" {
  description = "aws profile to use"
  type = string
}

variable "region_name" {
  default = "us-west-2"
  type = string
}

variable "candidate_name" {
  type = string
}

variable "env" {
  type = string
  default = "dev"
}

variable "project" {
    type = string
}
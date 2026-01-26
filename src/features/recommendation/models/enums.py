from enum import Enum

class AllergyType(str, Enum):
    LEGUMES = "LEGUMES"
    NUTS = "NUTS"
    SHELLFISH = "SHELLFISH"
    FISH = "FISH"
    GRAINS = "GRAINS"
    MILK = "MILK"
    SHRIMP = "SHRIMP"
    OYSTER = "OYSTER"
    CRAB = "CRAB"
    MUSSEL = "MUSSEL"
    SQUID = "SQUID"
    ABALONE = "ABALONE"
    MACKEREL = "MACKEREL"
    BUCKWHEAT = "BUCKWHEAT"
    WHEAT = "WHEAT"
    SOYBEAN = "SOYBEAN"
    WALNUT = "WALNUT"
    PEANUT = "PEANUT"
    PINE_NUT = "PINE_NUT"
    EGG = "EGG"
    BEEF = "BEEF"
    PORK = "PORK"
    CHICKEN = "CHICKEN"
    PEACH = "PEACH"
    TOMATO = "TOMATO"
    SULFITES = "SULFITES"

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class AgeGroup(str, Enum):
    TWENTIES = "TWENTIES"
    THIRTIES = "THIRTIES"
    FORTIES = "FORTIES"
    FIFTIES_PLUS = "FIFTIES_PLUS"

class DislikeType(str, Enum):
    SEAFOOD = "SEAFOOD"
    OFFAL = "OFFAL"
    RAW = "RAW"
    STRONG_SPICES = "STRONG_SPICES"

class OnboardingStatus(str, Enum):
    BASIC = "BASIC"
    CHARACTERISTIC = "CHARACTERISTIC"
    DONE = "DONE"